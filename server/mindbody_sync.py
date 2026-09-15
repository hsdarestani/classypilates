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
from sqlalchemy import func, select
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


def sync_from_mindbody() -> dict[str, int]:
    """Pull upcoming classes/visits, reconcile occupancy, and retain admin-only customer details."""
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
    counts = {"classes": 0, "visits": 0, "created": 0, "cancelled": 0}
    with core.SessionLocal() as db:
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
