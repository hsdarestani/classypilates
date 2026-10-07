"""One-shot, resumable Mindbody emergency export.

The exporter is intentionally read-only and has a hard logical API-call budget.
It stores raw provider responses so a future migration does not depend on the
current Classy application schema.
"""
from __future__ import annotations

import gzip
import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from mindbody_api import MindbodyError, _extract_list
from mindbody_sync import WriteClient


os.umask(0o077)

OUT = Path(os.getenv("MINDBODY_BACKUP_DIR", "/data/backups/mindbody/emergency-2026-10-08"))
CALL_BUDGET = max(100, int(os.getenv("MINDBODY_BACKUP_CALL_BUDGET", "25000")))
START_DATE = os.getenv("MINDBODY_BACKUP_START_DATE", "2010-01-01")
END_DATE = os.getenv(
    "MINDBODY_BACKUP_END_DATE",
    (datetime.now(timezone.utc) + timedelta(days=365)).date().isoformat(),
)
COST_PER_CALL = 0.002
EMERGENCY_EXPORT_PAUSED = True

OUT.mkdir(parents=True, exist_ok=True)
OUT.chmod(0o700)
STATE_PATH = OUT / "checkpoint.json"
MANIFEST_PATH = OUT / "manifest.json"
CALL_LOG = OUT / "api_calls.jsonl.gz"
ERROR_LOG = OUT / "errors.jsonl.gz"


class BudgetExceeded(RuntimeError):
    pass


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {
            "version": 1,
            "started_at": utcnow(),
            "logical_calls": 0,
            "completed": [],
            "client_complete_done": [],
            "client_visits_done": [],
            "client_contracts_done": [],
            "errors": 0,
        }
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {
            "version": 1,
            "started_at": utcnow(),
            "logical_calls": 0,
            "completed": [],
            "client_complete_done": [],
            "client_visits_done": [],
            "client_contracts_done": [],
            "errors": 0,
        }


STATE = load_state()


def save_state() -> None:
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(STATE, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(STATE_PATH)


def append_gz(path: Path, obj: Any) -> None:
    with gzip.open(path, "at", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))
        fh.write("\n")


def log_error(dataset: str, exc: Exception, **extra: Any) -> None:
    STATE["errors"] = int(STATE.get("errors", 0)) + 1
    append_gz(
        ERROR_LOG,
        {
            "at": utcnow(),
            "dataset": dataset,
            "type": type(exc).__name__,
            "error": str(exc)[:2000],
            **extra,
        },
    )
    save_state()


class BackupClient(WriteClient):
    def _reserve(self, method: str, path: str, params: Any = None) -> None:
        used = int(STATE.get("logical_calls", 0))
        if used >= CALL_BUDGET:
            raise BudgetExceeded(f"Mindbody backup call budget reached: {used}/{CALL_BUDGET}")
        STATE["logical_calls"] = used + 1
        append_gz(
            CALL_LOG,
            {
                "at": utcnow(),
                "n": STATE["logical_calls"],
                "method": method,
                "path": path,
                "params": params or {},
            },
        )
        if STATE["logical_calls"] % 25 == 0:
            save_state()

    def _authorized_get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        self._reserve("GET_AUTH", path, params)
        return super()._authorized_get(path, params)

    def _public_get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        self._reserve("GET_PUBLIC", path, params)
        return super()._public_get(path, params)

    def _write(self, path: str, payload: dict[str, Any], *, authenticated: bool = True) -> dict[str, Any]:
        # The backup only uses this for the user-token issue request.
        self._reserve("POST_AUTH" if authenticated else "POST_PUBLIC", path, {"keys": sorted(payload.keys())})
        return super()._write(path, payload, authenticated=authenticated)


CLIENT = BackupClient.from_env(timeout=30.0)


def rows_from(payload: Any, keys: Iterable[str]) -> list[dict[str, Any]]:
    rows = _extract_list(payload, tuple(keys))
    return [x for x in rows if isinstance(x, dict)]


def pagination(payload: Any) -> tuple[int | None, int | None]:
    if not isinstance(payload, dict):
        return None, None
    p = payload.get("PaginationResponse") or payload.get("paginationResponse") or {}
    if not isinstance(p, dict):
        return None, None
    total = p.get("TotalResults")
    size = p.get("PageSize")
    try:
        total = int(total) if total is not None else None
    except Exception:
        total = None
    try:
        size = int(size) if size is not None else None
    except Exception:
        size = None
    return total, size


def mark_done(name: str) -> None:
    done = set(STATE.get("completed", []))
    done.add(name)
    STATE["completed"] = sorted(done)
    save_state()


def export_single(name: str, path: str, *, params: dict[str, Any] | None = None, public: bool = False) -> None:
    if name in set(STATE.get("completed", [])):
        return
    try:
        payload = CLIENT._public_get(path, params or {}) if public else CLIENT._authorized_get(path, params or {})
        target = OUT / f"{name}.json.gz"
        with gzip.open(target, "wt", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        os.chmod(target, 0o600)
        mark_done(name)
        print(f"backup {name}: complete", flush=True)
    except BudgetExceeded:
        raise
    except Exception as exc:
        log_error(name, exc)
        print(f"backup {name}: ERROR {type(exc).__name__}: {str(exc)[:240]}", flush=True)


def export_paged(
    name: str,
    path: str,
    keys: tuple[str, ...],
    *,
    base_params: dict[str, Any] | None = None,
    public: bool = False,
    limit: int = 200,
) -> list[dict[str, Any]]:
    target = OUT / f"{name}.jsonl.gz"
    if name in set(STATE.get("completed", [])):
        # Only callers that need IDs use this on resume; reconstruct them.
        rows: list[dict[str, Any]] = []
        if target.exists():
            with gzip.open(target, "rt", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        item = json.loads(line)
                        if isinstance(item, dict) and item.get("_kind") == "row":
                            rows.append(item["data"])
                    except Exception:
                        pass
        return rows

    # Fresh collection export: overwrite any partial collection file. Collection
    # calls are cheap compared with per-client calls and this avoids ambiguous pages.
    if target.exists():
        target.unlink()
    offset = 0
    all_rows: list[dict[str, Any]] = []
    while True:
        params = dict(base_params or {})
        params["request.limit"] = limit
        params["request.offset"] = offset
        try:
            payload = CLIENT._public_get(path, params) if public else CLIENT._authorized_get(path, params)
        except BudgetExceeded:
            raise
        except Exception as exc:
            log_error(name, exc, offset=offset, path=path)
            print(f"backup {name}: ERROR at offset {offset}: {str(exc)[:240]}", flush=True)
            return all_rows

        rows = rows_from(payload, keys)
        for row in rows:
            append_gz(target, {"_kind": "row", "data": row})
        total, page_size = pagination(payload)
        append_gz(
            target,
            {
                "_kind": "page_meta",
                "offset": offset,
                "rows": len(rows),
                "total": total,
                "page_size": page_size,
            },
        )
        all_rows.extend(rows)
        print(f"backup {name}: offset={offset} rows={len(rows)} total={total}", flush=True)

        if total is not None and offset + len(rows) >= total:
            break
        if not rows or len(rows) < limit:
            break
        offset += len(rows)
    mark_done(name)
    return all_rows


def month_windows(start_iso: str, end_iso: str):
    start = date.fromisoformat(start_iso)
    end = date.fromisoformat(end_iso)
    cur = start.replace(day=1)
    while cur <= end:
        if cur.month == 12:
            nxt = date(cur.year + 1, 1, 1)
        else:
            nxt = date(cur.year, cur.month + 1, 1)
        yield cur, min(nxt - timedelta(days=1), end)
        cur = nxt


def export_windowed(
    name: str,
    path: str,
    keys: tuple[str, ...],
    param_start: str,
    param_end: str,
    *,
    extra_params: dict[str, Any] | None = None,
    public: bool = False,
) -> None:
    if name in set(STATE.get("completed", [])):
        return
    target = OUT / f"{name}.jsonl.gz"
    if target.exists():
        target.unlink()
    for start, end in month_windows(START_DATE, END_DATE):
        offset = 0
        while True:
            params = dict(extra_params or {})
            params[param_start] = f"{start.isoformat()}T00:00:00"
            params[param_end] = f"{end.isoformat()}T23:59:59"
            params["request.limit"] = 200
            params["request.offset"] = offset
            try:
                payload = CLIENT._public_get(path, params) if public else CLIENT._authorized_get(path, params)
            except BudgetExceeded:
                raise
            except Exception as exc:
                log_error(name, exc, start=start.isoformat(), end=end.isoformat(), offset=offset, path=path)
                print(
                    f"backup {name}: ERROR {start}..{end} offset={offset}: {str(exc)[:240]}",
                    flush=True,
                )
                break
            rows = rows_from(payload, keys)
            for row in rows:
                append_gz(
                    target,
                    {
                        "_kind": "row",
                        "window_start": start.isoformat(),
                        "window_end": end.isoformat(),
                        "data": row,
                    },
                )
            total, _ = pagination(payload)
            append_gz(
                target,
                {
                    "_kind": "page_meta",
                    "window_start": start.isoformat(),
                    "window_end": end.isoformat(),
                    "offset": offset,
                    "rows": len(rows),
                    "total": total,
                },
            )
            if total is not None and offset + len(rows) >= total:
                break
            if not rows or len(rows) < 200:
                break
            offset += len(rows)
    mark_done(name)
    print(f"backup {name}: complete", flush=True)


def client_id(row: dict[str, Any]) -> str:
    for key in ("Id", "ID", "ClientId", "ClientID", "id", "clientId"):
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def export_per_client(
    dataset: str,
    state_key: str,
    path: str,
    clients: list[dict[str, Any]],
    *,
    mode: str,
) -> None:
    done = set(str(x) for x in STATE.get(state_key, []))
    target = OUT / f"{dataset}.jsonl.gz"
    total_clients = len(clients)
    for idx, row in enumerate(clients, start=1):
        cid = client_id(row)
        if not cid or cid in done:
            continue
        try:
            if mode == "single":
                payload = CLIENT._authorized_get(path, {"request.clientId": cid})
                append_gz(target, {"client_id": cid, "payload": payload})
            elif mode == "visits":
                offset = 0
                while True:
                    params = {
                        "request.clientId": cid,
                        "request.startDate": f"{START_DATE}T00:00:00",
                        "request.endDate": f"{END_DATE}T23:59:59",
                        "request.limit": 200,
                        "request.offset": offset,
                    }
                    payload = CLIENT._authorized_get(path, params)
                    visits = rows_from(payload, ("Visits", "visits", "Items", "items"))
                    append_gz(
                        target,
                        {
                            "client_id": cid,
                            "offset": offset,
                            "rows": len(visits),
                            "payload": payload,
                        },
                    )
                    total, _ = pagination(payload)
                    if total is not None and offset + len(visits) >= total:
                        break
                    if not visits or len(visits) < 200:
                        break
                    offset += len(visits)
            elif mode == "contracts":
                offset = 0
                while True:
                    params = {
                        "request.clientId": cid,
                        "request.limit": 200,
                        "request.offset": offset,
                    }
                    payload = CLIENT._authorized_get(path, params)
                    rows2 = rows_from(payload, ("Contracts", "contracts", "ClientContracts", "Items", "items"))
                    append_gz(
                        target,
                        {
                            "client_id": cid,
                            "offset": offset,
                            "rows": len(rows2),
                            "payload": payload,
                        },
                    )
                    total, _ = pagination(payload)
                    if total is not None and offset + len(rows2) >= total:
                        break
                    if not rows2 or len(rows2) < 200:
                        break
                    offset += len(rows2)
            done.add(cid)
            STATE[state_key] = sorted(done)
            if len(done) % 10 == 0:
                save_state()
            if len(done) % 100 == 0:
                print(
                    f"backup {dataset}: {len(done)}/{total_clients} clients, calls={STATE['logical_calls']}",
                    flush=True,
                )
        except BudgetExceeded:
            STATE[state_key] = sorted(done)
            save_state()
            raise
        except Exception as exc:
            log_error(dataset, exc, client_id=cid)
            # Mark per-client errors as attempted to avoid an expensive retry loop
            # on every resume. Error details remain in errors.jsonl.gz.
            done.add(cid)
            STATE[state_key] = sorted(done)
            save_state()
    mark_done(dataset)
    save_state()
    print(f"backup {dataset}: complete {len(done)}/{total_clients}", flush=True)


def download_staff_images(staff: list[dict[str, Any]]) -> None:
    name = "staff_images"
    if name in set(STATE.get("completed", [])):
        return
    image_dir = OUT / "staff_images"
    image_dir.mkdir(exist_ok=True)
    image_dir.chmod(0o700)
    downloaded = 0
    for row in staff:
        sid = str(row.get("Id") or row.get("ID") or row.get("StaffId") or "unknown")
        urls: list[str] = []
        for key, value in row.items():
            if isinstance(value, str) and value.startswith("http") and ("image" in key.lower() or "photo" in key.lower()):
                urls.append(value)
        for num, url in enumerate(urls[:2]):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "ClassyPilatesBackup/1.0"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = resp.read()
                    ctype = (resp.headers.get("Content-Type") or "").lower()
                ext = ".jpg"
                if "png" in ctype:
                    ext = ".png"
                elif "webp" in ctype:
                    ext = ".webp"
                target = image_dir / f"{sid}-{num}{ext}"
                target.write_bytes(data)
                os.chmod(target, 0o600)
                downloaded += 1
            except Exception as exc:
                log_error(name, exc, staff_id=sid, url=url)
    mark_done(name)
    print(f"backup staff_images: downloaded={downloaded}", flush=True)


def write_manifest(status: str) -> None:
    files = []
    for p in sorted(OUT.rglob("*")):
        if p.is_file():
            try:
                files.append({"path": str(p.relative_to(OUT)), "bytes": p.stat().st_size})
            except Exception:
                pass
    manifest = {
        "status": status,
        "started_at": STATE.get("started_at"),
        "updated_at": utcnow(),
        "site_id": os.getenv("MINDBODY_SITE_ID", ""),
        "date_range": {"start": START_DATE, "end": END_DATE},
        "logical_api_calls": int(STATE.get("logical_calls", 0)),
        "call_budget": CALL_BUDGET,
        "estimated_api_cost_usd_at_0_002_per_call": round(int(STATE.get("logical_calls", 0)) * COST_PER_CALL, 2),
        "completed_datasets": STATE.get("completed", []),
        "errors": int(STATE.get("errors", 0)),
        "files": files,
    }
    tmp = MANIFEST_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    os.chmod(tmp, 0o600)
    tmp.replace(MANIFEST_PATH)


def main() -> int:
    if EMERGENCY_EXPORT_PAUSED:
        print(json.dumps({"ok": True, "status": "paused", "message": "Emergency Mindbody API export is paused to prevent further billable calls."}), flush=True)
        return 0
    try:
        # Site/catalog level data. Some optional endpoints can be disabled by the
        # account; failures are recorded without aborting the rest of the export.
        export_single("sites", "site/sites", public=True)
        export_single("locations", "site/locations", public=True)
        export_paged("programs", "site/programs", ("Programs", "programs", "Items"), public=True)
        export_paged("session_types", "site/sessiontypes", ("SessionTypes", "sessionTypes", "Items"), public=True)
        export_paged("resources", "site/resources", ("Resources", "resources", "Items"), public=True)
        export_paged("categories", "site/categories", ("Categories", "categories", "Items"))
        export_paged("payment_types", "site/paymenttypes", ("PaymentTypes", "paymentTypes", "Items"))
        export_paged("class_descriptions", "class/classdescriptions", ("ClassDescriptions", "classDescriptions", "Items"), public=True)
        staff = export_paged("staff", "staff/staff", ("StaffMembers", "Staff", "staff", "Items"))
        download_staff_images(staff)
        export_paged("services", "sale/services", ("Services", "services", "Items"))
        export_paged("products", "sale/products", ("Products", "products", "Items"))
        export_paged("packages", "sale/packages", ("Packages", "packages", "Items"))
        export_paged(
            "waitlist_entries",
            "class/waitlistentries",
            ("WaitlistEntries", "waitlistEntries", "Items"),
            base_params={"request.hidePastEntries": False},
        )

        # Historical operational/financial data in monthly windows.
        export_windowed(
            "classes",
            "class/classes",
            ("Classes", "classes", "Items"),
            "request.startDateTime",
            "request.endDateTime",
        )
        export_windowed(
            "sales",
            "sale/sales",
            ("Sales", "sales", "Items"),
            "request.startSaleDateTime",
            "request.endSaleDateTime",
        )
        export_windowed(
            "transactions",
            "sale/transactions",
            ("Transactions", "transactions", "Items"),
            "request.startDateTime",
            "request.endDateTime",
        )

        # Client directory first, then expensive per-client data. The latter is
        # resumable and bounded by CALL_BUDGET.
        clients = export_paged("clients", "client/clients", ("Clients", "clients", "Items"))
        export_per_client(
            "client_complete_info",
            "client_complete_done",
            "client/clientcompleteinfo",
            clients,
            mode="single",
        )
        export_per_client(
            "client_visits",
            "client_visits_done",
            "client/clientvisits",
            clients,
            mode="visits",
        )
        export_per_client(
            "client_contracts",
            "client_contracts_done",
            "client/clientcontracts",
            clients,
            mode="contracts",
        )

        save_state()
        write_manifest("complete")
        print(
            json.dumps(
                {
                    "ok": True,
                    "status": "complete",
                    "logical_api_calls": STATE["logical_calls"],
                    "estimated_cost_usd": round(STATE["logical_calls"] * COST_PER_CALL, 2),
                    "errors": STATE["errors"],
                    "output": str(OUT),
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return 0
    except BudgetExceeded as exc:
        save_state()
        write_manifest("budget_exhausted_resumable")
        print(
            json.dumps(
                {
                    "ok": False,
                    "status": "budget_exhausted_resumable",
                    "logical_api_calls": STATE["logical_calls"],
                    "estimated_cost_usd": round(STATE["logical_calls"] * COST_PER_CALL, 2),
                    "errors": STATE["errors"],
                    "output": str(OUT),
                    "message": str(exc),
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return 3
    except Exception as exc:
        log_error("fatal", exc)
        write_manifest("failed_resumable")
        print(
            json.dumps(
                {
                    "ok": False,
                    "status": "failed_resumable",
                    "logical_api_calls": STATE["logical_calls"],
                    "estimated_cost_usd": round(STATE["logical_calls"] * COST_PER_CALL, 2),
                    "errors": STATE["errors"],
                    "output": str(OUT),
                    "message": str(exc),
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
