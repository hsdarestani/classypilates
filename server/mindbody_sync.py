"""Production Mindbody booking mirror.

The synchronizer is deliberately idempotent: Mindbody visit IDs are unique locally,
and a paid website booking is never added twice. Failures remain visible and retryable.
"""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload

import main as core
from mindbody_api import MindbodyClient, MindbodyConfig, MindbodyError, _extract_list

SYNC_ENABLED = os.getenv("MINDBODY_SYNC_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
SYNC_INTERVAL = max(60, int(os.getenv("MINDBODY_SYNC_INTERVAL_SECONDS", "180")))
_worker_started = False
_worker_guard = threading.Lock()


def capability_status() -> dict[str, Any]:
    configured = bool(os.getenv("MINDBODY_API_KEY") and os.getenv("MINDBODY_STAFF_USERNAME") and os.getenv("MINDBODY_STAFF_PASSWORD"))
    return {"configured": configured, "enabled": SYNC_ENABLED, "interval_seconds": SYNC_INTERVAL}


def _ensure_sync_state() -> None:
    timestamp_type = "TIMESTAMP" if core.engine.dialect.name == "sqlite" else "TIMESTAMP WITH TIME ZONE"
    with core.engine.begin() as connection:
        connection.execute(text(f"""
            CREATE TABLE IF NOT EXISTS mindbody_sync_state (
                entity_type VARCHAR(32) NOT NULL,
                entity_id VARCHAR(100) NOT NULL,
                remote_id VARCHAR(100),
                local_changed_at {timestamp_type},
                remote_changed_at {timestamp_type},
                local_hash TEXT,
                remote_hash TEXT,
                last_synced_at {timestamp_type},
                sync_error TEXT,
                PRIMARY KEY (entity_type, entity_id)
            )
        """))


def _state_row(db: Session, entity_type: str, entity_id: int | str):
    _ensure_sync_state()
    return db.execute(
        text("SELECT * FROM mindbody_sync_state WHERE entity_type=:t AND entity_id=:i"),
        {"t": entity_type, "i": str(entity_id)},
    ).mappings().first()


def _state_write(
    db: Session,
    entity_type: str,
    entity_id: int | str,
    *,
    remote_id: str | None = None,
    local_changed_at: datetime | None = None,
    remote_changed_at: datetime | None = None,
    local_hash: str | None = None,
    remote_hash: str | None = None,
    last_synced_at: datetime | None = None,
    sync_error: str | None = None,
) -> None:
    _ensure_sync_state()
    db.execute(
        text("""
            INSERT INTO mindbody_sync_state
                (entity_type, entity_id, remote_id, local_changed_at, remote_changed_at, local_hash, remote_hash, last_synced_at, sync_error)
            VALUES
                (:t, :i, :remote_id, :local_changed_at, :remote_changed_at, :local_hash, :remote_hash, :last_synced_at, :sync_error)
            ON CONFLICT (entity_type, entity_id) DO UPDATE SET
                remote_id=COALESCE(excluded.remote_id, mindbody_sync_state.remote_id),
                local_changed_at=COALESCE(excluded.local_changed_at, mindbody_sync_state.local_changed_at),
                remote_changed_at=COALESCE(excluded.remote_changed_at, mindbody_sync_state.remote_changed_at),
                local_hash=COALESCE(excluded.local_hash, mindbody_sync_state.local_hash),
                remote_hash=COALESCE(excluded.remote_hash, mindbody_sync_state.remote_hash),
                last_synced_at=COALESCE(excluded.last_synced_at, mindbody_sync_state.last_synced_at),
                sync_error=COALESCE(excluded.sync_error, mindbody_sync_state.sync_error)
        """),
        {
            "t": entity_type,
            "i": str(entity_id),
            "remote_id": remote_id,
            "local_changed_at": local_changed_at,
            "remote_changed_at": remote_changed_at,
            "local_hash": local_hash,
            "remote_hash": remote_hash,
            "last_synced_at": last_synced_at,
            "sync_error": sync_error,
        },
    )


def mark_local_change(entity_type: str, entity_id: int | str) -> None:
    now = datetime.now(timezone.utc)
    with core.SessionLocal() as db:
        _state_write(db, entity_type, entity_id, local_changed_at=now, sync_error="")
        db.commit()


class WriteClient(MindbodyClient):
    def __init__(self, config: MindbodyConfig, timeout: float = 25.0):
        super().__init__(config, timeout)
        self.access_token = ""

    @classmethod
    def from_env(cls, timeout: float = 25.0):
        return cls(MindbodyConfig.from_env(), timeout)

    def _write(self, path: str, payload: dict[str, Any], *, authenticated: bool = True) -> dict[str, Any]:
        import json, urllib.error, urllib.request
        if authenticated and not self.access_token:
            self.issue_token()
        headers = {
            "API-Key": self.config.api_key, "SiteId": self.config.site_id,
            "Accept": "application/json", "Content-Type": "application/json", "User-Agent": "ClassyPilates/2.0",
        }
        if authenticated:
            headers["Authorization"] = self.access_token
        request = urllib.request.Request(
            f"{self.config.api_url}/{path.lstrip('/')}", data=json.dumps(payload).encode(), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            try:
                error = json.loads(detail).get("Error", {})
                detail = error.get("Message") or error.get("Code") or detail
            except Exception:
                pass
            raise MindbodyError(str(detail)[:1000], status=exc.code) from exc

    def issue_token(self) -> str:
        username = os.getenv("MINDBODY_STAFF_USERNAME", "").strip()
        password = os.getenv("MINDBODY_STAFF_PASSWORD", "")
        if not username or not password:
            raise MindbodyError("Mindbody staff credentials are not configured", code="not_configured")
        result = self._write("usertoken/issue", {"Username": username, "Password": password}, authenticated=False)
        self.access_token = str(result.get("AccessToken") or result.get("Token") or "")
        if not self.access_token:
            raise MindbodyError("Mindbody did not return a staff token", code="missing_token")
        return self.access_token

    def get_class_visits(self, class_id: str) -> dict[str, Any]:
        # Class visits contain the booking state and, when staff access permits it,
        # the customer object needed by the private admin panel.
        return self._authorized_get("class/classvisits", {"ClassId": class_id})

    def find_clients(self, email: str) -> list[dict[str, Any]]:
        payload = self._authorized_get("client/clients", {"SearchText": email, "Limit": 50})
        return [x for x in _extract_list(payload, ("Clients", "clients", "Items")) if isinstance(x, dict)]

    def _authorized_get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        import json, urllib.error, urllib.parse, urllib.request
        if not self.access_token: self.issue_token()
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
        request = urllib.request.Request(f"{self.config.api_url}/{path}?{query}", headers={
            "API-Key": self.config.api_key, "SiteId": self.config.site_id, "Authorization": self.access_token,
            "Accept": "application/json", "User-Agent": "ClassyPilates/2.0",
        })
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise MindbodyError(detail[:1000], status=exc.code) from exc

    def add_client(self, booking: core.Booking) -> str:
        parts = (booking.customer_name or "").strip().split(None, 1)
        result = self._write("client/addclient", {"Client": {
            "FirstName": parts[0] if parts else "Classy",
            "LastName": parts[1] if len(parts) > 1 else "Client",
            "Email": booking.email, "MobilePhone": booking.phone or "",
        }})
        client = result.get("Client") or result.get("client") or {}
        client_id = client.get("Id") or client.get("ID") or result.get("ClientId")
        if not client_id:
            raise MindbodyError("Mindbody client creation returned no client ID")
        return str(client_id)

    def add_to_class(self, client_id: str, class_id: str) -> dict[str, Any]:
        return self._write("class/addclienttoclass", {"ClientId": client_id, "ClassId": int(class_id), "RequirePayment": False})

    def get_staff(self, *, limit: int = 200, offset: int = 0) -> dict[str, Any]:
        return self._authorized_get("staff/staff", {"request.limit": limit, "request.offset": offset})

    def add_staff(self, *, display_name: str, bio: str = "") -> dict[str, Any]:
        parts = display_name.strip().split(None, 1)
        first_name = parts[0] if parts else "Classy"
        last_name = parts[1] if len(parts) > 1 else first_name
        return self._write("staff/addstaff", {
            "FirstName": first_name,
            "LastName": last_name,
            "Bio": bio or "",
            "ClassTeacher": True,
        })

    def update_staff(self, staff_id: str, *, display_name: str, bio: str, active: bool) -> dict[str, Any]:
        parts = display_name.strip().split(None, 1)
        payload: dict[str, Any] = {
            "ID": int(staff_id),
            "Bio": bio or "",
            "Active": bool(active),
            "ClassTeacher": True,
        }
        if parts:
            payload["FirstName"] = parts[0]
            payload["LastName"] = parts[1] if len(parts) > 1 else parts[0]
        return self._write("staff/updatestaff", payload)

    def substitute_class_teacher(self, class_id: str, staff_id: str) -> dict[str, Any]:
        return self._write("class/substituteclassteacher", {
            "ClassId": int(class_id),
            "StaffId": int(staff_id),
            "OverrideConflicts": False,
            "SendClientEmail": False,
            "SendOriginalTeacherEmail": False,
            "SendSubstituteTeacherEmail": False,
        })

    def remove_from_class(self, client_id: str, class_id: str) -> dict[str, Any]:
        return self._write("class/removeclientfromclass", {"ClientId": client_id, "ClassId": int(class_id), "LateCancel": False})


def _value(row: dict[str, Any], *names: str, default=None):
    for name in names:
        if row.get(name) is not None:
            return row[name]
    return default


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        from dateutil import parser
        parsed = parser.isoparse(str(value))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=core.ZoneInfo("Europe/Berlin"))
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _class_name(row: dict[str, Any]) -> str:
    description = row.get("ClassDescription") or {}
    return str(description.get("Name") or row.get("Name") or "").strip()


def _studio_name(row: dict[str, Any]) -> str:
    location = row.get("Location") or {}
    return str(location.get("Name") or row.get("LocationName") or "").strip().casefold()


def _studio_matches(local_id: str, name: str) -> bool:
    keys = {"bornheim": "bornheim", "sachsen": "sachsenhausen", "mid": "mid", "oval": "oval", "bhf1": "bahnhofsviertel", "ladies": "bahnhofsviertel"}
    return keys.get(local_id, local_id) in name


def _extract_visit(result: dict[str, Any]) -> dict[str, Any]:
    visit = result.get("Visit") or result.get("visit") or {}
    if visit:
        return visit
    visits = _extract_list(result, ("Visits", "visits", "Items"))
    return visits[0] if visits and isinstance(visits[0], dict) else {}


def sync_local_booking(booking_id: int) -> None:
    """Push one confirmed local booking to Mindbody; safe to call repeatedly."""
    with core.SessionLocal() as db:
        booking = db.scalar(select(core.Booking).options(joinedload(core.Booking.klass)).where(core.Booking.id == booking_id).with_for_update())
        if not booking or booking.source != "website" or booking.payment_status != "paid" or booking.status != "reserved":
            return
        if booking.mindbody_sync_status == "synced" and booking.mindbody_visit_id:
            return
        booking.mindbody_sync_status = "syncing"; booking.mindbody_sync_error = ""; db.commit()
        try:
            if not booking.klass.mindbody_class_id:
                sync_from_mindbody()
                db.refresh(booking.klass)
            if not booking.klass.mindbody_class_id:
                raise MindbodyError("No matching Mindbody class ID for this session")
            client = WriteClient.from_env()
            candidates = client.find_clients(booking.email)
            match = next((x for x in candidates if str(x.get("Email", "")).casefold() == booking.email.casefold()), None)
            client_id = str(_value(match or {}, "Id", "ID", default="")) or client.add_client(booking)
            result = client.add_to_class(client_id, booking.klass.mindbody_class_id)
            visit = _extract_visit(result)
            booking.mindbody_client_id = client_id
            booking.mindbody_visit_id = str(_value(visit, "Id", "ID", "VisitId", default="")) or f"client:{client_id}:class:{booking.klass.mindbody_class_id}"
            booking.mindbody_sync_status = "synced"; booking.mindbody_sync_error = ""; booking.mindbody_synced_at = datetime.now(timezone.utc)
        except Exception as exc:
            booking.mindbody_sync_status = "failed"; booking.mindbody_sync_error = str(exc)[:1500]
        db.commit()


def cancel_local_booking(booking_id: int) -> None:
    with core.SessionLocal() as db:
        booking = db.scalar(select(core.Booking).options(joinedload(core.Booking.klass)).where(core.Booking.id == booking_id).with_for_update())
        if not booking or booking.source != "website" or not booking.mindbody_client_id or not booking.klass.mindbody_class_id:
            return
        try:
            WriteClient.from_env().remove_from_class(booking.mindbody_client_id, booking.klass.mindbody_class_id)
            booking.mindbody_sync_status = "cancelled"; booking.mindbody_sync_error = ""; booking.mindbody_synced_at = datetime.now(timezone.utc)
        except Exception as exc:
            booking.mindbody_sync_status = "cancel_failed"; booking.mindbody_sync_error = str(exc)[:1500]
        db.commit()


def _coach_payload(coach: core.Coach) -> dict[str, Any]:
    return {
        "display_name": (coach.display_name or "").strip(),
        "bio": (coach.bio or "").strip(),
        "photo_url": (coach.photo_url or "").strip(),
        "active": bool(coach.active),
    }


def _remote_staff_payload(row: dict[str, Any]) -> dict[str, Any]:
    first = str(_value(row, "FirstName", "firstName", default="") or "").strip()
    last = str(_value(row, "LastName", "lastName", default="") or "").strip()
    display = str(_value(row, "DisplayName", "displayName", default="") or "").strip()
    if not display:
        display = " ".join(x for x in (first, last) if x).strip()
    active = _value(row, "Active", "active", default=True)
    return {
        "display_name": display,
        "bio": str(_value(row, "Bio", "Biography", "bio", "biography", default="") or "").strip(),
        "photo_url": str(_value(row, "ImageUrl", "ImageURL", "imageUrl", "imageURL", default="") or "").strip(),
        "active": bool(active),
    }


def _stable_hash(payload: dict[str, Any]) -> str:
    import hashlib, json
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _remote_staff_id(row: dict[str, Any]) -> str:
    return str(_value(row, "Id", "ID", "StaffId", "staffId", default="") or "")


def _staff_result_id(result: dict[str, Any]) -> str:
    row = result.get("Staff") or result.get("staff") or {}
    return _remote_staff_id(row) or str(result.get("StaffId") or result.get("staffId") or "")


def _load_remote_staff(client: WriteClient) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        payload = client.get_staff(limit=200, offset=offset)
        batch = [x for x in _extract_list(payload, ("StaffMembers", "staffMembers", "Staff", "staff", "Items")) if isinstance(x, dict)]
        rows.extend(batch)
        if len(batch) < 200:
            break
        offset += len(batch)
    return rows


def _sync_staff_profiles(client: WriteClient, db: Session, now: datetime) -> tuple[dict[str, int], dict[str, core.Coach]]:
    _ensure_sync_state()
    counts = {
        "staff_remote": 0,
        "staff_created_local": 0,
        "staff_created_remote": 0,
        "staff_pulled": 0,
        "staff_pushed": 0,
        "staff_errors": 0,
    }
    remote_rows = _load_remote_staff(client)
    counts["staff_remote"] = len(remote_rows)
    locals_ = db.scalars(select(core.Coach)).all()
    by_name = {(x.display_name or "").strip().casefold(): x for x in locals_ if (x.display_name or "").strip()}
    state_rows = db.execute(text("SELECT * FROM mindbody_sync_state WHERE entity_type='coach'")).mappings().all() if locals_ else []
    local_by_remote: dict[str, core.Coach] = {}
    for state in state_rows:
        if state.get("remote_id"):
            try:
                coach = db.get(core.Coach, int(state["entity_id"]))
            except Exception:
                coach = None
            if coach:
                local_by_remote[str(state["remote_id"])] = coach

    mapped: dict[str, core.Coach] = {}
    seen_local_ids: set[int] = set()
    for remote in remote_rows:
        remote_id = _remote_staff_id(remote)
        if not remote_id:
            continue
        rp = _remote_staff_payload(remote)
        coach = local_by_remote.get(remote_id) or by_name.get(rp["display_name"].casefold())
        if coach is None:
            coach = core.Coach(
                display_name=rp["display_name"] or f"Mindbody Staff {remote_id}",
                photo_url=rp["photo_url"],
                bio=rp["bio"],
                active=rp["active"],
            )
            db.add(coach)
            db.flush()
            counts["staff_created_local"] += 1
        seen_local_ids.add(coach.id)
        mapped[remote_id] = coach

        state = _state_row(db, "coach", coach.id)
        old_remote_hash = str((state or {}).get("remote_hash") or "")
        remote_hash = _stable_hash(rp)
        local_payload = _coach_payload(coach)
        local_hash = _stable_hash(local_payload)
        remote_changed_at = now if old_remote_hash and old_remote_hash != remote_hash else (state or {}).get("remote_changed_at")
        if not remote_changed_at:
            remote_changed_at = now
        local_changed_at = (state or {}).get("local_changed_at")

        # Initial linking: Mindbody is authoritative for provider-backed fields.
        local_is_newer = bool(local_changed_at and local_changed_at > remote_changed_at and old_remote_hash)
        try:
            if local_is_newer:
                result = client.update_staff(
                    remote_id,
                    display_name=local_payload["display_name"],
                    bio=local_payload["bio"],
                    active=local_payload["active"],
                )
                returned = result.get("Staff") or result.get("staff")
                if isinstance(returned, dict):
                    rp = _remote_staff_payload(returned)
                    remote_hash = _stable_hash(rp)
                counts["staff_pushed"] += 1
            else:
                changed = False
                if rp["display_name"] and coach.display_name != rp["display_name"]:
                    coach.display_name = rp["display_name"]; changed = True
                if coach.bio != rp["bio"]:
                    coach.bio = rp["bio"]; changed = True
                if coach.active != rp["active"]:
                    coach.active = rp["active"]; changed = True
                # Mindbody exposes staff image URLs for reads, but its public Staff update endpoint
                # does not support image upload. Pull remote images unless a newer local profile edit exists.
                if rp["photo_url"] and (not local_changed_at or local_changed_at <= remote_changed_at) and coach.photo_url != rp["photo_url"]:
                    coach.photo_url = rp["photo_url"]; changed = True
                if changed:
                    counts["staff_pulled"] += 1
            _state_write(
                db, "coach", coach.id,
                remote_id=remote_id,
                remote_changed_at=remote_changed_at,
                local_hash=_stable_hash(_coach_payload(coach)),
                remote_hash=remote_hash,
                last_synced_at=now,
                sync_error="",
            )
        except Exception as exc:
            counts["staff_errors"] += 1
            _state_write(db, "coach", coach.id, remote_id=remote_id, last_synced_at=now, sync_error=str(exc)[:1000])

    # Local-only coaches are created in Mindbody so future local changes become provider-backed.
    for coach in locals_:
        if coach.id in seen_local_ids or not (coach.display_name or "").strip():
            continue
        state = _state_row(db, "coach", coach.id)
        if (state or {}).get("remote_id"):
            continue
        if coach.display_name.strip().casefold() == "classy coach":
            continue
        try:
            result = client.add_staff(display_name=coach.display_name, bio=coach.bio or "")
            remote_id = _staff_result_id(result)
            if not remote_id:
                raise MindbodyError("Mindbody staff creation returned no staff ID")
            if not coach.active:
                client.update_staff(remote_id, display_name=coach.display_name, bio=coach.bio or "", active=False)
            mapped[remote_id] = coach
            counts["staff_created_remote"] += 1
            _state_write(
                db, "coach", coach.id,
                remote_id=remote_id,
                local_hash=_stable_hash(_coach_payload(coach)),
                last_synced_at=now,
                sync_error="",
            )
        except Exception as exc:
            counts["staff_errors"] += 1
            _state_write(db, "coach", coach.id, last_synced_at=now, sync_error=str(exc)[:1000])

    db.flush()
    return counts, mapped


def _sync_class_coach(
    client: WriteClient,
    db: Session,
    klass: core.ClassSession,
    remote: dict[str, Any],
    staff_map: dict[str, core.Coach],
    now: datetime,
) -> tuple[int, int, int]:
    remote_staff = remote.get("Staff") or remote.get("staff") or {}
    remote_staff_id = _remote_staff_id(remote_staff)
    if not remote_staff_id:
        return 0, 0, 0
    state = _state_row(db, "class", klass.id)
    local_changed_at = (state or {}).get("local_changed_at")
    remote_modified = _parse_dt(_value(remote, "LastModifiedDateTime", "lastModifiedDateTime"))
    if not remote_modified:
        remote_modified = (state or {}).get("remote_changed_at") or now
    previous_remote_id = str((state or {}).get("remote_id") or "")
    remote_changed = bool(previous_remote_id and previous_remote_id != remote_staff_id)
    local_is_newer = bool(local_changed_at and local_changed_at > remote_modified and previous_remote_id)

    try:
        if local_is_newer and klass.coach_id:
            local_coach = db.get(core.Coach, klass.coach_id)
            coach_state = _state_row(db, "coach", local_coach.id) if local_coach else None
            local_remote_staff_id = str((coach_state or {}).get("remote_id") or "")
            if local_remote_staff_id and local_remote_staff_id != remote_staff_id:
                client.substitute_class_teacher(str(klass.mindbody_class_id), local_remote_staff_id)
                _state_write(
                    db, "class", klass.id,
                    remote_id=local_remote_staff_id,
                    remote_changed_at=now,
                    last_synced_at=now,
                    sync_error="",
                )
                return 0, 1, 0
        remote_coach = staff_map.get(remote_staff_id)
        if remote_coach and klass.coach_id != remote_coach.id:
            klass.coach_id = remote_coach.id
            _state_write(
                db, "class", klass.id,
                remote_id=remote_staff_id,
                remote_changed_at=remote_modified,
                last_synced_at=now,
                sync_error="",
            )
            return 1, 0, 0
        _state_write(
            db, "class", klass.id,
            remote_id=remote_staff_id,
            remote_changed_at=remote_modified if remote_changed or not previous_remote_id else None,
            last_synced_at=now,
            sync_error="",
        )
        return 0, 0, 0
    except Exception as exc:
        _state_write(db, "class", klass.id, last_synced_at=now, sync_error=str(exc)[:1000])
        return 0, 0, 1


def sync_from_mindbody() -> dict[str, int]:
    """Pull upcoming classes/visits, reconcile occupancy, staff profiles, and trainer assignments."""
    client = WriteClient.from_env()
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=45)
    classes: list[dict[str, Any]] = []
    offset = 0
    while True:
        payload = client.get_classes(start_date_time=now.isoformat(), end_date_time=end.isoformat(), limit=200, offset=offset)
        batch = [x for x in _extract_list(payload, ("Classes", "classes", "Items")) if isinstance(x, dict)]
        classes.extend(batch)
        if len(batch) < 200: break
        offset += len(batch)
    counts = {
        "classes": 0, "visits": 0, "created": 0, "cancelled": 0,
        "trainer_assignments_pulled": 0, "trainer_assignments_pushed": 0, "trainer_assignment_errors": 0,
    }
    with core.SessionLocal() as db:
        staff_counts, staff_map = _sync_staff_profiles(client, db, now)
        counts.update(staff_counts)
        local = db.scalars(select(core.ClassSession).where(core.ClassSession.starts_at >= now, core.ClassSession.starts_at < end)).all()
        for remote in classes:
            remote_id = str(_value(remote, "Id", "ID", "ClassId", default=""))
            starts = _parse_dt(_value(remote, "StartDateTime", "startDateTime"))
            if not remote_id or not starts: continue
            klass = next((x for x in local if x.mindbody_class_id == remote_id), None)
            if not klass:
                klass = next((x for x in local if abs((core.as_utc(x.starts_at)-starts).total_seconds()) < 90 and x.title.casefold() == _class_name(remote).casefold() and _studio_matches(x.studio_id, _studio_name(remote))), None)
            if not klass: continue
            klass.mindbody_class_id = remote_id; klass.mindbody_synced_at = now
            pulled, pushed, assignment_errors = _sync_class_coach(client, db, klass, remote, staff_map, now)
            counts["trainer_assignments_pulled"] += pulled
            counts["trainer_assignments_pushed"] += pushed
            counts["trainer_assignment_errors"] += assignment_errors
            klass.capacity = max(klass.capacity, int(_value(remote, "MaxCapacity", "Capacity", default=klass.capacity) or klass.capacity))
            counts["classes"] += 1
            try:
                payload = client.get_class_visits(remote_id)
            except MindbodyError:
                # Occupancy still remains safe when the account cannot expose PII.
                total = int(_value(remote, "TotalBooked", "TotalClients", default=0) or 0)
                local_synced = db.scalar(select(func.count(core.Booking.id)).where(core.Booking.class_id == klass.id, core.Booking.source == "website", core.Booking.status == "reserved", core.Booking.mindbody_sync_status == "synced")) or 0
                klass.imported_bookings = max(0, total - int(local_synced))
                continue
            visits = [x for x in _extract_list(payload, ("Visits", "visits", "ClassVisits", "Items")) if isinstance(x, dict)]
            active_ids: set[str] = set()
            for visit in visits:
                visit_id = str(_value(visit, "Id", "ID", "VisitId", default=""))
                client_data = visit.get("Client") or {}
                client_id = str(_value(visit, "ClientId", default=_value(client_data, "Id", "ID", default="")))
                if not visit_id: visit_id = f"client:{client_id}:class:{remote_id}"
                if bool(_value(visit, "Cancelled", "IsCancelled", default=False)): continue
                active_ids.add(visit_id); counts["visits"] += 1
                booking = db.scalar(select(core.Booking).where(core.Booking.mindbody_visit_id == visit_id))
                if booking:
                    booking.status = "reserved"; booking.mindbody_synced_at = now
                    continue
                # Link back a just-pushed website booking before creating an external row.
                booking = db.scalar(select(core.Booking).where(core.Booking.class_id == klass.id, core.Booking.source == "website", core.Booking.mindbody_client_id == client_id)) if client_id else None
                if booking:
                    booking.mindbody_visit_id = visit_id; booking.mindbody_sync_status = "synced"; booking.mindbody_synced_at = now
                    continue
                name = " ".join(str(client_data.get(k) or "").strip() for k in ("FirstName", "LastName")).strip()
                email = str(client_data.get("Email") or f"mindbody-{client_id or visit_id}@private.invalid").lower()
                db.add(core.Booking(reference=f"MB-{visit_id}"[:40], class_id=klass.id, customer_name=name or "Mindbody client", email=email,
                    phone=str(client_data.get("MobilePhone") or ""), status="reserved", payment_status="external", payment_method="mindbody",
                    amount_cents=0, source="mindbody", mindbody_visit_id=visit_id, mindbody_client_id=client_id,
                    mindbody_sync_status="synced", mindbody_synced_at=now))
                counts["created"] += 1
            mirrored = db.scalars(select(core.Booking).where(core.Booking.class_id == klass.id, core.Booking.source == "mindbody", core.Booking.status == "reserved")).all()
            for booking in mirrored:
                if booking.mindbody_visit_id not in active_ids:
                    booking.status = "cancelled"; booking.mindbody_synced_at = now; counts["cancelled"] += 1
            klass.imported_bookings = 0  # individual mirror rows are counted by the normal booking query
            klass.source_bookings_total = len(active_ids)
        db.commit()
    return counts


def retry_pending() -> int:
    with core.SessionLocal() as db:
        ids = list(db.scalars(select(core.Booking.id).where(core.Booking.source == "website", core.Booking.status == "reserved", core.Booking.payment_status == "paid", core.Booking.mindbody_sync_status.in_(["pending", "failed"])).limit(100)))
    for booking_id in ids: sync_local_booking(booking_id)
    return len(ids)


def _loop():
    while True:
        try:
            if capability_status()["configured"]:
                sync_from_mindbody(); retry_pending()
        except Exception as exc:
            print(f"Mindbody mirror cycle failed: {type(exc).__name__}: {str(exc)[:300]}", flush=True)
        time.sleep(SYNC_INTERVAL)


@core.app.on_event("startup")
def start_worker():
    global _worker_started
    if not SYNC_ENABLED or not capability_status()["configured"]: return
    with _worker_guard:
        if _worker_started: return
        _worker_started = True
        threading.Thread(target=_loop, name="mindbody-mirror", daemon=True).start()


@core.app.post("/api/staff/mindbody/sync")
def manual_sync(background: BackgroundTasks, user: core.User = Depends(core.require("bookings.manage"))):
    background.add_task(sync_from_mindbody)
    background.add_task(retry_pending)
    return {"ok": True, "queued": True}


@core.app.get("/api/staff/mindbody/status")
def mirror_status(user: core.User = Depends(core.require("bookings.view")), db: Session = Depends(core.db_session)):
    failed = db.scalar(select(func.count(core.Booking.id)).where(core.Booking.mindbody_sync_status.in_(["failed", "cancel_failed"]))) or 0
    pending = db.scalar(select(func.count(core.Booking.id)).where(core.Booking.source == "website", core.Booking.mindbody_sync_status == "pending", core.Booking.payment_status == "paid")) or 0
    last = db.scalar(select(func.max(core.ClassSession.mindbody_synced_at)))
    return {**capability_status(), "failed": int(failed), "pending": int(pending), "last_synced_at": last.isoformat() if last else None}
