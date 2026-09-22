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
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session, joinedload

import main as core
from mindbody_api import MindbodyClient, MindbodyConfig, MindbodyError, _extract_list

SYNC_ENABLED = os.getenv("MINDBODY_SYNC_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
SYNC_INTERVAL = max(60, int(os.getenv("MINDBODY_SYNC_INTERVAL_SECONDS", "180")))
INITIAL_SYNC_DELAY = max(0, int(os.getenv("MINDBODY_INITIAL_SYNC_DELAY_SECONDS", "180")))
_worker_started = False
_worker_guard = threading.Lock()


def capability_status() -> dict[str, Any]:
    configured = bool(os.getenv("MINDBODY_API_KEY") and os.getenv("MINDBODY_STAFF_USERNAME") and os.getenv("MINDBODY_STAFF_PASSWORD"))
    return {
        "configured": configured,
        "enabled": SYNC_ENABLED,
        "interval_seconds": SYNC_INTERVAL,
        "initial_delay_seconds": INITIAL_SYNC_DELAY,
    }


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
    _ensure_sync_state()
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

    def get_classes(
        self,
        *,
        start_date_time: str | None = None,
        end_date_time: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, Any]:
        # Use staff authorization so hidden/cancelled classes and capacity fields are
        # visible consistently, even when consumer-mode settings mask them publicly.
        return self._authorized_get("class/classes", {
            "request.startDateTime": start_date_time,
            "request.endDateTime": end_date_time,
            "request.hideCanceledClasses": False,
            "request.limit": limit,
            "request.offset": offset,
        })

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

    def add_client_details(self, *, email: str, first_name: str, last_name: str, phone: str = "") -> str:
        result = self._write("client/addclient", {"Client": {
            "FirstName": first_name.strip(),
            "LastName": last_name.strip(),
            "Email": email.strip().lower(),
            "MobilePhone": phone.strip(),
        }})
        client = result.get("Client") or result.get("client") or {}
        client_id = client.get("Id") or client.get("ID") or result.get("ClientId")
        if not client_id:
            raise MindbodyError("Mindbody client creation returned no client ID")
        return str(client_id)

    def add_client(self, booking: core.Booking) -> str:
        parts = (booking.customer_name or "").strip().split(None, 1)
        return self.add_client_details(
            email=booking.email,
            first_name=parts[0] if parts else "Classy",
            last_name=parts[1] if len(parts) > 1 else "Client",
            phone=booking.phone or "",
        )

    def add_to_class(self, client_id: str, class_id: str, *, waitlist: bool = False) -> dict[str, Any]:
        return self._write("class/addclienttoclass", {
            "ClientId": client_id,
            "ClassId": int(class_id),
            "RequirePayment": False,
            "Waitlist": bool(waitlist),
            "SendEmail": False,
        })

    def get_waitlist_entries(
        self,
        *,
        class_id: str | None = None,
        client_id: str | None = None,
        waitlist_entry_id: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"request.hidePastEntries": True, "request.limit": 100}
        if class_id:
            params["request.classIds"] = [int(class_id)]
        if client_id:
            params["request.clientIds"] = [client_id]
        if waitlist_entry_id:
            params["request.waitlistEntryIds"] = [int(waitlist_entry_id)]
        payload = self._authorized_get("class/waitlistentries", params)
        return [
            x for x in _extract_list(payload, ("WaitlistEntries", "waitlistEntries", "Items"))
            if isinstance(x, dict)
        ]

    def remove_from_waitlist(self, waitlist_entry_id: str) -> None:
        import urllib.error, urllib.parse, urllib.request
        if not self.access_token:
            self.issue_token()
        query = urllib.parse.urlencode(
            [("request.waitlistEntryIds", int(waitlist_entry_id))],
            doseq=True,
        )
        request = urllib.request.Request(
            f"{self.config.api_url}/class/removefromwaitlist?{query}",
            data=b"",
            method="POST",
            headers={
                "API-Key": self.config.api_key,
                "SiteId": self.config.site_id,
                "Authorization": self.access_token,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "ClassyPilates/2.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout):
                return
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise MindbodyError(detail[:1000], status=exc.code) from exc

    def cancel_single_class(self, class_id: str) -> dict[str, Any]:
        return self._write("class/cancelsingleclass", {
            "ClassID": int(class_id),
            "HideCancel": True,
            "SendClientEmail": False,
            "SendStaffEmail": False,
        })

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


def _find_remote_class(client: WriteClient, klass: core.ClassSession) -> dict[str, Any] | None:
    if not klass.mindbody_class_id:
        return None
    starts = core.as_utc(klass.starts_at)
    payload = client.get_classes(
        start_date_time=(starts - timedelta(hours=2)).isoformat(),
        end_date_time=(starts + timedelta(hours=2)).isoformat(),
        limit=100,
        offset=0,
    )
    target = str(klass.mindbody_class_id)
    return next(
        (
            row for row in _extract_list(payload, ("Classes", "classes", "Items"))
            if isinstance(row, dict) and str(_value(row, "Id", "ID", "ClassId", default="") or "") == target
        ),
        None,
    )


def refresh_class_availability_strict(class_id: int) -> dict[str, int | bool]:
    """Refresh one class from Mindbody immediately before a booking attempt."""
    with core.SessionLocal() as db:
        klass = db.get(core.ClassSession, class_id)
        if not klass or not klass.mindbody_class_id:
            return {"provider_backed": False}
        client = WriteClient.from_env()
        remote = _find_remote_class(client, klass)
        if not remote:
            raise MindbodyError("Mindbody class is not available")
        if bool(_value(remote, "IsCanceled", "IsCancelled", "Cancelled", "isCanceled", default=False)):
            raise MindbodyError("Mindbody class is cancelled")
        live_reserved = db.scalar(
            select(func.count(core.Booking.id)).where(
                core.Booking.class_id == klass.id,
                core.Booking.status == "reserved",
            )
        ) or 0
        _sync_class_availability(db, klass, remote, int(live_reserved))
        klass.mindbody_synced_at = datetime.now(timezone.utc)
        db.commit()
        expected = max(0, int(klass.capacity or 0) - int(klass.imported_bookings or 0) - int(live_reserved))
        return {"provider_backed": True, "spots": expected, "cancelled": False}


def _sync_or_hold_local_booking(booking_id: int, *, allow_pending: bool) -> None:
    """Create/confirm the provider reservation before Classy reports success."""
    with core.SessionLocal() as db:
        booking = db.scalar(
            select(core.Booking)
            .options(joinedload(core.Booking.klass))
            .where(core.Booking.id == booking_id)
            .with_for_update()
        )
        if not booking or booking.source != "website" or booking.status != "reserved":
            return
        allowed_payment = booking.payment_status == "paid" or (allow_pending and booking.payment_status == "pending")
        if not allowed_payment:
            return
        if booking.mindbody_sync_status == "synced" and booking.mindbody_visit_id:
            return
        booking.mindbody_sync_status = "syncing"
        booking.mindbody_sync_error = ""
        db.commit()
        try:
            if not booking.klass.mindbody_class_id:
                sync_from_mindbody()
                db.refresh(booking.klass)
            if not booking.klass.mindbody_class_id:
                raise MindbodyError("No matching Mindbody class ID for this session")

            client = WriteClient.from_env()
            remote = _find_remote_class(client, booking.klass)
            if not remote:
                raise MindbodyError("Mindbody class is not available")
            if bool(_value(remote, "IsCanceled", "IsCancelled", "Cancelled", "isCanceled", default=False)):
                raise MindbodyError("Mindbody class is cancelled")

            cap = _value(remote, "MaxCapacity", "Capacity", default=None)
            booked = _value(remote, "TotalBooked", "TotalClients", default=None)
            web_cap = _value(remote, "WebCapacity", default=None)
            web_booked = _value(remote, "TotalWebBooked", "WebBooked", default=None)
            is_available = _value(remote, "IsAvailable", "isAvailable", default=True)
            if is_available is False:
                raise MindbodyError("Mindbody class is not available for booking")
            if cap is not None and booked is not None and int(booked) >= int(cap):
                raise MindbodyError("Mindbody class is full")
            if web_cap is not None and web_booked is not None and int(web_booked) >= int(web_cap):
                raise MindbodyError("Mindbody online booking capacity is full")

            candidates = client.find_clients(booking.email)
            match = next((x for x in candidates if str(x.get("Email", "")).casefold() == booking.email.casefold()), None)
            client_id = str(_value(match or {}, "Id", "ID", default="")) or client.add_client(booking)
            result = client.add_to_class(client_id, booking.klass.mindbody_class_id)
            visit = _extract_visit(result)
            booking.mindbody_client_id = client_id
            booking.mindbody_visit_id = str(_value(visit, "Id", "ID", "VisitId", default="")) or f"client:{client_id}:class:{booking.klass.mindbody_class_id}"

            # Staff-authenticated AddClientToClass can be more permissive than the
            # consumer booking window. Verify that our write did not overbook.
            remote_after = _find_remote_class(client, booking.klass)
            if remote_after:
                cap_after = _value(remote_after, "MaxCapacity", "Capacity", default=None)
                booked_after = _value(remote_after, "TotalBooked", "TotalClients", default=None)
                web_cap_after = _value(remote_after, "WebCapacity", default=None)
                web_booked_after = _value(remote_after, "TotalWebBooked", "WebBooked", default=None)
                over_physical = cap_after is not None and booked_after is not None and int(booked_after) > int(cap_after)
                over_web = web_cap_after is not None and web_booked_after is not None and int(web_booked_after) > int(web_cap_after)
                if over_physical or over_web:
                    try:
                        client.remove_from_class(client_id, booking.klass.mindbody_class_id)
                    finally:
                        raise MindbodyError("Mindbody class became full during booking")

            booking.mindbody_sync_status = "synced"
            booking.mindbody_sync_error = ""
            booking.mindbody_synced_at = datetime.now(timezone.utc)
        except Exception as exc:
            booking.mindbody_sync_status = "failed"
            booking.mindbody_sync_error = str(exc)[:1500]
        db.commit()


def hold_local_booking(booking_id: int) -> None:
    _sync_or_hold_local_booking(booking_id, allow_pending=True)


def sync_local_booking(booking_id: int) -> None:
    _sync_or_hold_local_booking(booking_id, allow_pending=False)


def _waitlist_entry_id(row: dict[str, Any]) -> str:
    return str(_value(row, "Id", "ID", "WaitlistEntryId", "WaitlistEntryID", default="") or "")


def _waitlist_client_id(row: dict[str, Any]) -> str:
    client = row.get("Client") or row.get("client") or {}
    return str(_value(row, "ClientId", "ClientID", default=_value(client, "Id", "ID", default="")) or "")


def add_remote_waitlist(
    *,
    class_id: str,
    email: str,
    first_name: str,
    last_name: str,
    phone: str = "",
) -> tuple[str, str]:
    client = WriteClient.from_env()
    candidates = client.find_clients(email)
    match = next((x for x in candidates if str(x.get("Email", "")).casefold() == email.casefold()), None)
    client_id = str(_value(match or {}, "Id", "ID", default="") or "")
    if not client_id:
        if len(first_name.strip()) < 2 or len(last_name.strip()) < 2:
            raise MindbodyError("waitlist_name_required")
        client_id = client.add_client_details(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
        )

    client.add_to_class(client_id, class_id, waitlist=True)
    entries = client.get_waitlist_entries(class_id=class_id, client_id=client_id)
    matches = [x for x in entries if _waitlist_client_id(x) == client_id]
    if not matches:
        raise MindbodyError("Mindbody waitlist entry could not be verified")
    entry_id = _waitlist_entry_id(matches[-1])
    if not entry_id:
        raise MindbodyError("Mindbody waitlist entry has no ID")
    return client_id, entry_id


def remove_remote_waitlist(waitlist_entry_id: str) -> None:
    if not waitlist_entry_id:
        return
    client = WriteClient.from_env()
    try:
        client.remove_from_waitlist(waitlist_entry_id)
    except Exception:
        # Mindbody may treat repeated removals as errors. Verify absence before failing.
        entries = client.get_waitlist_entries(waitlist_entry_id=waitlist_entry_id)
        if any(_waitlist_entry_id(x) == str(waitlist_entry_id) for x in entries):
            raise


def _remote_booking_is_active(client: WriteClient, booking: core.Booking) -> bool:
    if not booking.klass.mindbody_class_id:
        return False
    payload = client.get_class_visits(str(booking.klass.mindbody_class_id))
    visits = [x for x in _extract_list(payload, ("Visits", "visits", "ClassVisits", "Items")) if isinstance(x, dict)]
    for visit in visits:
        if bool(_value(visit, "Cancelled", "IsCancelled", default=False)):
            continue
        client_data = visit.get("Client") or {}
        visit_id = str(_value(visit, "Id", "ID", "VisitId", default="") or "")
        client_id = str(_value(visit, "ClientId", "ClientID", default=_value(client_data, "Id", "ID", default="")) or "")
        if booking.mindbody_visit_id and visit_id and visit_id == str(booking.mindbody_visit_id):
            return True
        if booking.mindbody_client_id and client_id and client_id == str(booking.mindbody_client_id):
            return True
    return False


def cancel_local_booking_strict(booking_id: int) -> bool:
    """Remove a website booking from Mindbody before Classy confirms cancellation."""
    with core.SessionLocal() as db:
        booking = db.scalar(
            select(core.Booking)
            .options(joinedload(core.Booking.klass))
            .where(core.Booking.id == booking_id)
            .with_for_update()
        )
        if not booking or booking.source != "website":
            return True
        if not booking.mindbody_client_id or not booking.klass.mindbody_class_id:
            # No provider-side reservation exists yet.
            return True

        client = WriteClient.from_env()
        try:
            client.remove_from_class(str(booking.mindbody_client_id), str(booking.klass.mindbody_class_id))
        except Exception:
            # A repeated cancellation may be reported as an error by Mindbody.
            # Treat it as success only after verifying that the visit is no longer active.
            try:
                if _remote_booking_is_active(client, booking):
                    raise
            except MindbodyError:
                raise
        booking.mindbody_sync_status = "cancelled"
        booking.mindbody_sync_error = ""
        booking.mindbody_synced_at = datetime.now(timezone.utc)
        db.commit()
        return True


def cancel_local_booking(booking_id: int) -> None:
    try:
        cancel_local_booking_strict(booking_id)
    except Exception as exc:
        with core.SessionLocal() as db:
            booking = db.get(core.Booking, booking_id)
            if booking:
                booking.mindbody_sync_status = "cancel_failed"
                booking.mindbody_sync_error = str(exc)[:1500]
                booking.mindbody_synced_at = datetime.now(timezone.utc)
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


def _remote_staff_modified(row: dict[str, Any]) -> datetime | None:
    return _parse_dt(_value(
        row,
        "LastModifiedDateTime", "lastModifiedDateTime",
        "LastModifiedDate", "lastModifiedDate",
        "ModifiedDateTime", "modifiedDateTime",
    ))


def _is_managed_local_photo(value: str) -> bool:
    return str(value or "").startswith("/api/media/coach-photos/")


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
        explicit_remote_modified = _remote_staff_modified(remote)
        remote_changed_at = explicit_remote_modified or (
            now if old_remote_hash and old_remote_hash != remote_hash else (state or {}).get("remote_changed_at")
        )
        if not remote_changed_at:
            remote_changed_at = now
        local_changed_at = (state or {}).get("local_changed_at")

        # Preserve locally uploaded coach photos that predate sync-state tracking.
        # Treat the current local managed image as the latest version until Mindbody
        # provides a later explicit modification timestamp.
        if _is_managed_local_photo(coach.photo_url) and not local_changed_at:
            local_changed_at = now
            _state_write(db, "coach", coach.id, local_changed_at=local_changed_at)

        # Initial linking: Mindbody is authoritative for provider-backed text fields,
        # except when Classy has a tracked newer edit.
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
                # Never replace a locally uploaded image with an older/undated Mindbody image.
                # A remote image may replace it only when Mindbody exposes an explicit modification
                # timestamp that is newer than the tracked local edit.
                remote_photo_is_newer = bool(
                    explicit_remote_modified
                    and (not local_changed_at or explicit_remote_modified > local_changed_at)
                )
                may_pull_photo = (
                    not _is_managed_local_photo(coach.photo_url)
                    or remote_photo_is_newer
                )
                if rp["photo_url"] and may_pull_photo and coach.photo_url != rp["photo_url"]:
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
        # Historical coaches imported from old Mindbody exports are not evidence
        # of a newer local change. Only create a new remote Staff record when the
        # coach has actually been created/edited in Classy after sync tracking began.
        if not state or not state.get("local_changed_at"):
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


def _remote_class_studio_id(remote: dict[str, Any]) -> str | None:
    from import_mindbody_schedule import studio_id
    return studio_id(_studio_name(remote), _class_name(remote))


def _remote_class_duration(remote: dict[str, Any], starts: datetime) -> int:
    end = _parse_dt(_value(remote, "EndDateTime", "endDateTime"))
    if end and end > starts:
        return max(15, min(180, int(round((end - starts).total_seconds() / 60))))
    raw = _value(remote, "Duration", "DurationMinutes", "duration", "durationMinutes", default=50)
    try:
        return max(15, min(180, int(raw or 50)))
    except Exception:
        return 50


def _remote_class_description(remote: dict[str, Any]) -> str:
    desc = remote.get("ClassDescription") or remote.get("classDescription") or {}
    return str(_value(desc, "Description", "description", default="") or "").strip()[:2000]


def _dedupe_mindbody_classes(db: Session) -> int:
    duplicate_ids = list(db.scalars(
        select(core.ClassSession.mindbody_class_id)
        .where(core.ClassSession.mindbody_class_id.is_not(None))
        .group_by(core.ClassSession.mindbody_class_id)
        .having(func.count(core.ClassSession.id) > 1)
    ))
    if not duplicate_ids:
        # Older production schemas received mindbody_class_id via ALTER TABLE, so the
        # ORM-level unique=True was never materialized as an index. Enforce it now.
        db.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_classes_mindbody_class_id "
            "ON classes (mindbody_class_id) WHERE mindbody_class_id IS NOT NULL"
        ))
        db.commit()
        return 0

    tables = set(inspect(core.engine).get_table_names())
    merged = 0
    for remote_id in duplicate_ids:
        rows = list(db.scalars(
            select(core.ClassSession)
            .where(core.ClassSession.mindbody_class_id == remote_id)
            .order_by(core.ClassSession.id.asc())
        ))
        if len(rows) < 2:
            continue

        # Keep the oldest row: it is the one most likely to already own bookings and
        # public links from before the live Mindbody mirror was introduced.
        survivor = rows[0]
        for duplicate in rows[1:]:
            if "bookings" in tables:
                db.execute(text("UPDATE bookings SET class_id=:keep WHERE class_id=:drop"), {"keep": survivor.id, "drop": duplicate.id})
            if "waitlist" in tables:
                db.execute(text("UPDATE waitlist SET class_id=:keep WHERE class_id=:drop"), {"keep": survivor.id, "drop": duplicate.id})
            if "class_notifications" in tables:
                db.execute(text("UPDATE class_notifications SET class_id=:keep WHERE class_id=:drop"), {"keep": survivor.id, "drop": duplicate.id})
            if "public_class_map" in tables:
                survivor_map = db.execute(
                    text("SELECT external_id FROM public_class_map WHERE class_id=:keep LIMIT 1"),
                    {"keep": survivor.id},
                ).first()
                if survivor_map:
                    db.execute(text("DELETE FROM public_class_map WHERE class_id=:drop"), {"drop": duplicate.id})
                else:
                    db.execute(text("UPDATE public_class_map SET class_id=:keep WHERE class_id=:drop"), {"keep": survivor.id, "drop": duplicate.id})
            if "mindbody_sync_state" in tables:
                db.execute(
                    text("DELETE FROM mindbody_sync_state WHERE entity_type='class' AND entity_id=:drop"),
                    {"drop": str(duplicate.id)},
                )
            db.delete(duplicate)
            merged += 1
        db.flush()

    db.commit()
    db.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_classes_mindbody_class_id "
        "ON classes (mindbody_class_id) WHERE mindbody_class_id IS NOT NULL"
    ))
    db.commit()
    return merged


def _ensure_local_class(
    db: Session,
    local: list[core.ClassSession],
    remote: dict[str, Any],
    staff_map: dict[str, core.Coach],
    now: datetime,
) -> tuple[core.ClassSession | None, bool]:
    remote_id = str(_value(remote, "Id", "ID", "ClassId", default="") or "")
    starts = _parse_dt(_value(remote, "StartDateTime", "startDateTime"))
    title = _class_name(remote)
    if not remote_id or not starts or not title:
        return None, False

    # Mindbody's class endpoint may include earlier classes from the current day even
    # when StartDateTime is set to "now". Look up the provider ID across the whole DB,
    # not only the future-window list, otherwise those rows are recreated every sync.
    klass = db.scalar(
        select(core.ClassSession)
        .where(core.ClassSession.mindbody_class_id == remote_id)
        .order_by(core.ClassSession.id.asc())
        .limit(1)
    )
    if klass:
        if all(x.id != klass.id for x in local):
            local.append(klass)
        return klass, False

    klass = next(
        (
            x for x in local
            if abs((core.as_utc(x.starts_at) - starts).total_seconds()) < 90
            and x.title.casefold() == title.casefold()
            and _studio_matches(x.studio_id, _studio_name(remote))
        ),
        None,
    )
    if klass:
        klass.mindbody_class_id = remote_id
        klass.mindbody_synced_at = now
        return klass, False

    target_studio_id = _remote_class_studio_id(remote)
    if not target_studio_id or not db.get(core.Studio, target_studio_id):
        return None, False

    from import_mindbody_schedule import class_type
    remote_staff = remote.get("Staff") or remote.get("staff") or {}
    remote_staff_id = _remote_staff_id(remote_staff)
    coach = staff_map.get(remote_staff_id)
    capacity_raw = _value(remote, "MaxCapacity", "Capacity", default=10)
    try:
        capacity = max(1, min(100, int(capacity_raw or 10)))
    except Exception:
        capacity = 10

    klass = core.ClassSession(
        studio_id=target_studio_id,
        title=title[:180],
        description=_remote_class_description(remote),
        class_type=class_type(title),
        coach_id=coach.id if coach else None,
        starts_at=starts,
        duration=_remote_class_duration(remote, starts),
        capacity=capacity,
        imported_bookings=0,
        source_bookings_total=0,
        mindbody_class_id=remote_id,
        mindbody_synced_at=now,
        status="active",
        created_by=None,
    )
    db.add(klass)
    db.flush()
    local.append(klass)
    return klass, True


def _remote_class_cancelled(remote: dict[str, Any]) -> bool:
    return bool(_value(
        remote,
        "IsCanceled", "IsCancelled", "Cancelled", "isCanceled", "isCancelled",
        default=False,
    ))


def _sync_remote_class_metadata(
    klass: core.ClassSession,
    remote: dict[str, Any],
    now: datetime,
) -> bool:
    """Pull provider-owned schedule metadata for a Mindbody-backed class instance."""
    starts = _parse_dt(_value(remote, "StartDateTime", "startDateTime"))
    title = _class_name(remote)
    studio_id = _remote_class_studio_id(remote)
    changed = False

    if title and klass.title != title[:180]:
        klass.title = title[:180]
        changed = True
    description = _remote_class_description(remote)
    if klass.description != description:
        klass.description = description
        changed = True
    if title:
        from import_mindbody_schedule import class_type
        remote_type = class_type(title)
        if klass.class_type != remote_type:
            klass.class_type = remote_type
            changed = True
    if studio_id and klass.studio_id != studio_id:
        klass.studio_id = studio_id
        changed = True
    if starts and abs((core.as_utc(klass.starts_at) - starts).total_seconds()) > 1:
        klass.starts_at = starts
        changed = True
    if starts:
        duration = _remote_class_duration(remote, starts)
        if klass.duration != duration:
            klass.duration = duration
            changed = True

    target_status = "cancelled" if _remote_class_cancelled(remote) else "active"
    if klass.status != target_status:
        klass.status = target_status
        changed = True

    klass.mindbody_synced_at = now
    return changed


def _sync_class_availability(
    db: Session,
    klass: core.ClassSession,
    remote: dict[str, Any],
    local_reserved: int,
) -> bool:
    """Make Classy public availability match Mindbody without fetching the roster."""
    def as_int(*names: str) -> int | None:
        value = _value(remote, *names, default=None)
        if value is None or value == "":
            return None
        try:
            return int(value)
        except Exception:
            return None

    remote_capacity = as_int("MaxCapacity", "Capacity")
    web_capacity = as_int("WebCapacity")
    total_booked = as_int("TotalBooked", "TotalClients")
    web_booked = as_int("TotalWebBooked", "WebBooked", "TotalWebClients")

    changed = False

    # Mindbody is authoritative for physical capacity. Do not keep an older/larger
    # Classy capacity after the provider changed it.
    if remote_capacity is not None and remote_capacity >= 0 and klass.capacity != remote_capacity:
        klass.capacity = remote_capacity
        changed = True

    effective_capacity = remote_capacity if remote_capacity is not None and remote_capacity >= 0 else int(klass.capacity or 0)
    if effective_capacity < 0:
        effective_capacity = 0

    if total_booked is not None:
        total_booked = max(0, total_booked)
        physical_available = max(0, effective_capacity - total_booked)
        available = physical_available

        # If Mindbody applies a separate web booking cap, website availability must
        # respect the stricter of physical capacity and web capacity.
        if web_capacity is not None and web_capacity >= 0 and web_booked is not None:
            web_available = max(0, web_capacity - max(0, web_booked))
            available = min(available, web_available)

        target_reserved = max(0, effective_capacity - available)
        imported = max(0, target_reserved - max(0, int(local_reserved)))
        if int(klass.imported_bookings or 0) != imported:
            klass.imported_bookings = imported
            changed = True
        if int(klass.source_bookings_total or 0) != total_booked:
            klass.source_bookings_total = total_booked
            changed = True

    return changed


def sync_staff_and_assignments() -> dict[str, int]:
    """Synchronize Mindbody staff profiles and upcoming class trainer assignments only.

    This intentionally skips class rosters/bookings so it is safe for deployment-time
    verification and completes quickly. The normal background mirror continues to own
    booking, cancellation, and occupancy reconciliation.
    """
    client = WriteClient.from_env()
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=45)
    classes: list[dict[str, Any]] = []
    offset = 0
    while True:
        payload = client.get_classes(
            start_date_time=now.isoformat(),
            end_date_time=end.isoformat(),
            limit=200,
            offset=offset,
        )
        batch = [x for x in _extract_list(payload, ("Classes", "classes", "Items")) if isinstance(x, dict)]
        classes.extend(batch)
        if len(batch) < 200:
            break
        offset += len(batch)

    counts = {
        "classes_seen": len(classes),
        "classes_matched": 0,
        "classes_created_local": 0,
        "classes_skipped_unmapped": 0,
        "metadata_updated": 0,
        "availability_updated": 0,
        "trainer_assignments_pulled": 0,
        "trainer_assignments_pushed": 0,
        "trainer_assignment_errors": 0,
    }
    with core.SessionLocal() as db:
        counts["duplicate_classes_merged"] = _dedupe_mindbody_classes(db)
        staff_counts, staff_map = _sync_staff_profiles(client, db, now)
        counts.update(staff_counts)
        local = db.scalars(
            select(core.ClassSession).where(
                core.ClassSession.starts_at >= now,
                core.ClassSession.starts_at < end,
            )
        ).all()
        local_ids = [row.id for row in local]
        reserved_counts: dict[int, int] = {}
        if local_ids:
            reserved_counts = dict(
                db.execute(
                    select(core.Booking.class_id, func.count(core.Booking.id))
                    .where(
                        core.Booking.class_id.in_(local_ids),
                        core.Booking.status == "reserved",
                    )
                    .group_by(core.Booking.class_id)
                ).all()
            )
        for remote in classes:
            klass, created_local = _ensure_local_class(db, local, remote, staff_map, now)
            if not klass:
                counts["classes_skipped_unmapped"] += 1
                continue
            if created_local:
                counts["classes_created_local"] += 1
                reserved_counts.setdefault(klass.id, 0)
            if _sync_remote_class_metadata(klass, remote, now):
                counts["metadata_updated"] += 1
            if _sync_class_availability(
                db,
                klass,
                remote,
                int(reserved_counts.get(klass.id, 0)),
            ):
                counts["availability_updated"] += 1
            pulled, pushed, assignment_errors = _sync_class_coach(client, db, klass, remote, staff_map, now)
            counts["classes_matched"] += 1
            counts["trainer_assignments_pulled"] += pulled
            counts["trainer_assignments_pushed"] += pushed
            counts["trainer_assignment_errors"] += assignment_errors
        db.commit()
    return counts


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
        "classes_created_local": 0, "classes_skipped_unmapped": 0,
        "trainer_assignments_pulled": 0, "trainer_assignments_pushed": 0, "trainer_assignment_errors": 0,
    }
    with core.SessionLocal() as db:
        counts["duplicate_classes_merged"] = _dedupe_mindbody_classes(db)
        staff_counts, staff_map = _sync_staff_profiles(client, db, now)
        counts.update(staff_counts)
        local = db.scalars(select(core.ClassSession).where(core.ClassSession.starts_at >= now, core.ClassSession.starts_at < end)).all()
        for remote in classes:
            remote_id = str(_value(remote, "Id", "ID", "ClassId", default=""))
            klass, created_local = _ensure_local_class(db, local, remote, staff_map, now)
            if not klass:
                counts["classes_skipped_unmapped"] += 1
                continue
            if created_local:
                counts["classes_created_local"] += 1
            pulled, pushed, assignment_errors = _sync_class_coach(client, db, klass, remote, staff_map, now)
            counts["trainer_assignments_pulled"] += pulled
            counts["trainer_assignments_pushed"] += pushed
            counts["trainer_assignment_errors"] += assignment_errors
            klass.capacity = max(klass.capacity, int(_value(remote, "MaxCapacity", "Capacity", default=klass.capacity) or klass.capacity))
            counts["classes"] += 1

            # Release DB locks before the remote roster request. Mindbody network calls
            # can be slow and must never keep a database transaction open.
            db.commit()
            try:
                payload = client.get_class_visits(remote_id)
            except MindbodyError:
                # Occupancy still remains safe when the account cannot expose PII.
                total = int(_value(remote, "TotalBooked", "TotalClients", default=0) or 0)
                local_synced = db.scalar(select(func.count(core.Booking.id)).where(core.Booking.class_id == klass.id, core.Booking.source == "website", core.Booking.status == "reserved", core.Booking.mindbody_sync_status == "synced")) or 0
                klass.imported_bookings = max(0, total - int(local_synced))
                db.commit()
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
        db.commit()
    return counts


def retry_pending() -> int:
    with core.SessionLocal() as db:
        ids = list(db.scalars(
            select(core.Booking.id).where(
                core.Booking.source == "website",
                core.Booking.status == "reserved",
                core.Booking.payment_status == "paid",
                core.Booking.mindbody_sync_status.in_(["pending", "failed"]),
            ).limit(100)
        ))
        cancel_ids = list(db.scalars(
            select(core.Booking.id).where(
                core.Booking.source == "website",
                core.Booking.status == "cancelled",
                core.Booking.mindbody_sync_status == "cancel_failed",
            ).limit(100)
        ))
    for booking_id in ids:
        sync_local_booking(booking_id)
    for booking_id in cancel_ids:
        cancel_local_booking(booking_id)
    return len(ids) + len(cancel_ids)


def _loop():
    if INITIAL_SYNC_DELAY:
        time.sleep(INITIAL_SYNC_DELAY)
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
