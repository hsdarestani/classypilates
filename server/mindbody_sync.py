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
from mindbody_availability import compute_public_availability
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session, joinedload

import main as core
from mindbody_api import MindbodyClient, MindbodyConfig, MindbodyError, _extract_list

SYNC_ENABLED = os.getenv("MINDBODY_SYNC_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
SYNC_INTERVAL = max(60, int(os.getenv("MINDBODY_SYNC_INTERVAL_SECONDS", "180")))
INITIAL_SYNC_DELAY = max(0, int(os.getenv("MINDBODY_INITIAL_SYNC_DELAY_SECONDS", "180")))
_worker_started = False
_worker_guard = threading.Lock()
_sync_state_ready = False
_sync_state_guard = threading.Lock()

# Serialize roster/availability reconciliation across the polling mirror, manual
# syncs, and webhook-triggered targeted refreshes. Database uniqueness remains the
# final guard, but avoiding overlapping provider reads/writes prevents transient
# duplicate attempts and stale counters during high-volume booking bursts.
RECONCILE_LOCK = threading.RLock()


def capability_status() -> dict[str, Any]:
    configured = bool(os.getenv("MINDBODY_API_KEY") and os.getenv("MINDBODY_STAFF_USERNAME") and os.getenv("MINDBODY_STAFF_PASSWORD"))
    return {
        "configured": configured,
        "enabled": SYNC_ENABLED,
        "interval_seconds": SYNC_INTERVAL,
        "initial_delay_seconds": INITIAL_SYNC_DELAY,
    }


def _ensure_sync_state() -> None:
    """Create sync-state storage once per process, never in the hot sync path.

    PostgreSQL DDL can wait on unrelated transactions even with IF NOT EXISTS.
    The previous implementation ran this DDL every three minutes while holding the
    global Mindbody reconciliation lock, which could freeze both polling and webhook
    workers indefinitely. Cache successful initialization and enforce a short DB
    lock timeout so a transient database lock becomes retryable instead.
    """
    global _sync_state_ready
    if _sync_state_ready:
        return
    with _sync_state_guard:
        if _sync_state_ready:
            return
        timestamp_type = "TIMESTAMP" if core.engine.dialect.name == "sqlite" else "TIMESTAMP WITH TIME ZONE"
        with core.engine.begin() as connection:
            if core.engine.dialect.name == "postgresql":
                connection.execute(text("SET LOCAL lock_timeout = '5s'"))
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
            duplicate_coach_remote = connection.execute(text("""
                SELECT 1
                FROM mindbody_sync_state
                WHERE entity_type='coach' AND remote_id IS NOT NULL AND remote_id <> ''
                GROUP BY remote_id
                HAVING count(*) > 1
                LIMIT 1
            """)).first()
            if not duplicate_coach_remote:
                connection.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS ux_mindbody_sync_coach_remote_id
                    ON mindbody_sync_state (remote_id)
                    WHERE entity_type='coach' AND remote_id IS NOT NULL
                """))
        _sync_state_ready = True


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
    _token_cache = ""
    _token_expires_at = 0.0
    _token_guard = threading.Lock()

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
        now = time.time()
        with self._token_guard:
            if self._token_cache and now < self._token_expires_at:
                self.access_token = self._token_cache
                return self.access_token
            username = os.getenv("MINDBODY_STAFF_USERNAME", "").strip()
            password = os.getenv("MINDBODY_STAFF_PASSWORD", "")
            if not username or not password:
                raise MindbodyError("Mindbody staff credentials are not configured", code="not_configured")
            result = self._write("usertoken/issue", {"Username": username, "Password": password}, authenticated=False)
            token = str(result.get("AccessToken") or result.get("Token") or "")
            if not token:
                raise MindbodyError("Mindbody did not return a staff token", code="missing_token")
            self.access_token = token
            self.__class__._token_cache = token
            self.__class__._token_expires_at = now + 600
            return self.access_token

    def get_class_visits(self, class_id: str) -> dict[str, Any]:
        # V6 requires the request-scoped query key exactly as request.classID.
        # Using ClassId is silently treated as an unfiltered/invalid request by
        # Mindbody and can yield an empty roster instead of a clear error.
        return self._authorized_get(
            "class/classvisits",
            {"request.classID": int(class_id)},
        )

    def get_classes(
        self,
        *,
        start_date_time: str | None = None,
        end_date_time: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        public_only: bool = False,
    ) -> dict[str, Any]:
        params = {
            "request.startDateTime": start_date_time,
            "request.endDateTime": end_date_time,
            "request.hideCanceledClasses": True if public_only else False,
            "request.limit": limit,
            "request.offset": offset,
        }
        # Mindbody V6 intentionally returns hidden/cancelled classes to an
        # authenticated staff request. Public schedule mirroring must therefore use
        # the unauthenticated/public-visible feed; staff auth is reserved for
        # lifecycle, roster and write operations.
        if public_only:
            return self._public_get("class/classes", params)
        return self._authorized_get("class/classes", params)

    def find_clients(self, email: str) -> list[dict[str, Any]]:
        payload = self._authorized_get("client/clients", {"SearchText": email, "Limit": 50})
        return [x for x in _extract_list(payload, ("Clients", "clients", "Items")) if isinstance(x, dict)]

    def _public_get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        import json, urllib.error, urllib.parse, urllib.request
        query = urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None},
            doseq=True,
        )
        request = urllib.request.Request(
            f"{self.config.api_url}/{path}?{query}",
            headers={
                "API-Key": self.config.api_key,
                "SiteId": self.config.site_id,
                "Accept": "application/json",
                "User-Agent": "ClassyPilates/2.0",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise MindbodyError(detail[:1000], status=exc.code) from exc

    def _authorized_get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        import json, urllib.error, urllib.parse, urllib.request
        if not self.access_token: self.issue_token()
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
        request = urllib.request.Request(f"{self.config.api_url}/{path}?{query}", headers={
            "API-Key": self.config.api_key, "SiteId": self.config.site_id, "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json", "User-Agent": "ClassyPilates/2.0",
        })
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise MindbodyError(detail[:1000], status=exc.code) from exc

    def add_client_details(self, *, email: str, first_name: str, last_name: str, phone: str = "") -> str:
        result = self._write("client/addclient", {
            "FirstName": first_name.strip(),
            "LastName": last_name.strip(),
            "Email": email.strip().lower(),
            "MobilePhone": phone.strip(),
            "Active": True,
        })
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
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "request.hidePastEntries": True,
            "request.limit": max(1, min(200, int(limit))),
            "request.offset": max(0, int(offset)),
        }
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


def _extract_class_visits(payload: Any) -> list[dict[str, Any]]:
    """Return visits from Mindbody GetClassVisits response.

    V6 returns a Class object whose Visits collection is nested under "Class".
    Accept the old/top-level shapes as a defensive fallback, but never assume
    Visits lives at the response root.
    """
    if not isinstance(payload, dict):
        return []
    container = payload.get("Class") or payload.get("class") or payload
    rows = _extract_list(container, ("Visits", "visits", "ClassVisits", "Items"))
    if not rows and container is not payload:
        rows = _extract_list(payload, ("Visits", "visits", "ClassVisits", "Items"))
    return [row for row in rows if isinstance(row, dict)]


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
        public_only=True,
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
    """Create/confirm the provider reservation without holding a DB connection during provider I/O."""
    try:
        with core.SessionLocal() as db:
            booking = db.scalar(
                select(core.Booking)
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
            if booking.mindbody_sync_status == "syncing":
                return

            klass = booking.klass
            if not klass.mindbody_class_id:
                booking.mindbody_sync_status = "failed"
                booking.mindbody_sync_error = "No matching Mindbody class ID for this session"
                db.commit()
                return

            previous_client_id = ""
            if not booking.mindbody_client_id:
                previous_client_id = str(db.scalar(
                    select(core.Booking.mindbody_client_id)
                    .where(
                        func.lower(core.Booking.email) == booking.email.lower(),
                        core.Booking.mindbody_client_id.is_not(None),
                        core.Booking.id != booking.id,
                    )
                    .order_by(core.Booking.created_at.desc())
                    .limit(1)
                ) or "")

            snapshot = {
                "email": booking.email,
                "customer_name": booking.customer_name or "",
                "phone": booking.phone or "",
                "client_id": str(booking.mindbody_client_id or previous_client_id or ""),
                "class_id": str(klass.mindbody_class_id),
                "klass": klass,
                "synced_at": klass.mindbody_synced_at,
            }
            booking.mindbody_sync_status = "syncing"
            booking.mindbody_sync_error = ""
            db.commit()

        # Important: no SQLAlchemy Session is kept open across these network calls.
        # A slow Mindbody response must never consume the app's DB connection pool.
        client = WriteClient.from_env(timeout=10.0)
        remote = None
        synced_at = snapshot["synced_at"]
        recently_checked = bool(
            synced_at
            and (datetime.now(timezone.utc) - core.as_utc(synced_at)).total_seconds() < 45
        )
        if not recently_checked:
            remote = _find_remote_class(client, snapshot["klass"])
        else:
            remote = {"IsAvailable": True}

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

        client_id = snapshot["client_id"]
        if not client_id:
            candidates = client.find_clients(snapshot["email"])
            match = next(
                (
                    x for x in candidates
                    if str(x.get("Email", "")).casefold() == snapshot["email"].casefold()
                ),
                None,
            )
            client_id = str(_value(match or {}, "Id", "ID", default="") or "")
            if not client_id:
                parts = snapshot["customer_name"].strip().split(None, 1)
                client_id = client.add_client_details(
                    email=snapshot["email"],
                    first_name=parts[0] if parts else "Classy",
                    last_name=parts[1] if len(parts) > 1 else "Client",
                    phone=snapshot["phone"],
                )

        with core.SessionLocal() as db:
            current = db.get(core.Booking, booking_id)
            if not current or current.status != "reserved":
                return
            current.mindbody_client_id = client_id
            current.mindbody_sync_status = "syncing"
            db.commit()

        result = client.add_to_class(client_id, snapshot["class_id"])
        visit = _extract_visit(result)
        visit_id = str(_value(visit, "Id", "ID", "VisitId", default="")) or f"client:{client_id}:class:{snapshot['class_id']}"

        with core.SessionLocal() as db:
            current = db.scalar(
                select(core.Booking)
                .where(core.Booking.id == booking_id)
                .with_for_update()
            )
            if not current:
                return
            current.mindbody_client_id = client_id
            current.mindbody_visit_id = visit_id
            current.mindbody_sync_status = "synced"
            current.mindbody_sync_error = ""
            current.mindbody_synced_at = datetime.now(timezone.utc)
            db.commit()
    except Exception as exc:
        with core.SessionLocal() as db:
            current = db.get(core.Booking, booking_id)
            if current and current.mindbody_sync_status != "synced":
                current.mindbody_sync_status = "failed"
                current.mindbody_sync_error = str(exc)[:1500]
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

    # Heal a remote-only waitlist row instead of creating a second one.
    existing_entries = client.get_waitlist_entries(class_id=class_id, client_id=client_id)
    existing = [
        row for row in existing_entries
        if _waitlist_client_id(row) == client_id and _waitlist_entry_id(row)
    ]
    if existing:
        return client_id, _waitlist_entry_id(existing[-1])

    result = client.add_to_class(client_id, class_id, waitlist=True)
    visit = _extract_visit(result)
    entry_id = str(_value(
        result,
        "WaitlistEntryId", "WaitlistEntryID",
        default=_value(visit, "WaitlistEntryId", "WaitlistEntryID", default=""),
    ) or "")
    if entry_id:
        return client_id, entry_id

    # Waitlist reads can lag the write very briefly. Poll a few times before treating
    # the operation as unverifiable.
    for attempt in range(4):
        entries = client.get_waitlist_entries(class_id=class_id, client_id=client_id)
        matches = [x for x in entries if _waitlist_client_id(x) == client_id]
        if matches:
            entry_id = _waitlist_entry_id(matches[-1])
            if entry_id:
                return client_id, entry_id
        if attempt < 3:
            time.sleep(0.5 * (attempt + 1))
    raise MindbodyError("Mindbody waitlist entry could not be verified")


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
    """Remove any provider-backed booking from Mindbody before confirming cancellation."""
    with core.SessionLocal() as db:
        booking = db.scalar(
            select(core.Booking)
            .where(core.Booking.id == booking_id)
            .with_for_update()
        )
        if not booking:
            return True
        if not booking.klass.mindbody_class_id:
            booking.mindbody_sync_status = "cancelled"
            booking.mindbody_sync_error = ""
            booking.mindbody_synced_at = datetime.now(timezone.utc)
            db.commit()
            return True

        visit_id = str(booking.mindbody_visit_id or "").strip()
        client_id = str(booking.mindbody_client_id or "").strip()

        # A website booking that never reached Mindbody has nothing remote to
        # cancel. A Mindbody-origin booking without either identity is not safe to
        # cancel locally because we cannot identify the upstream reservation.
        if not client_id and not visit_id:
            if booking.source == "website" and booking.mindbody_sync_status in {"pending", "failed", "local"}:
                booking.mindbody_sync_status = "cancelled"
                booking.mindbody_sync_error = ""
                booking.mindbody_synced_at = datetime.now(timezone.utc)
                db.commit()
                return True
            raise MindbodyError("Cannot identify the Mindbody reservation to cancel")

        client = WriteClient.from_env()
        try:
            payload: dict[str, Any] = {
                "ClassId": int(booking.klass.mindbody_class_id),
                "LateCancel": False,
            }
            if client_id:
                payload["ClientId"] = client_id
            if visit_id.isdigit():
                payload["VisitId"] = int(visit_id)
            client._write("class/removeclientfromclass", payload)
        except Exception:
            # Repeated cancellation can return an error. Treat it as success only
            # after a roster read proves the reservation is no longer active.
            if _remote_booking_is_active(client, booking):
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
    display = _canonical_coach_name(display)
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


def _canonical_coach_name(value: str) -> str:
    value = " ".join(str(value or "").split()).strip()
    if value.casefold().startswith("coach "):
        value = value[6:].strip()
    parts = [part for part in value.split() if part]
    if len(parts) == 2 and parts[0].casefold() == parts[1].casefold():
        parts = [parts[0]]
    return " ".join(parts)


def _mindbody_staff_write_name(local_display_name: str, remote_row: dict[str, Any] | None = None) -> str:
    canonical = _canonical_coach_name(local_display_name)
    if not canonical:
        return ""
    raw_remote = ""
    if remote_row:
        raw_remote = str(_value(remote_row, "DisplayName", "displayName", default="") or "").strip()
    if raw_remote.casefold().startswith("coach "):
        return f"Coach {canonical}"
    if canonical.casefold() == "classy fitness":
        return canonical
    # Classy Pilates' Mindbody directory uses the "Coach " role prefix for
    # scheduled instructors. Keep that provider convention while Classy displays
    # the cleaner canonical name.
    return f"Coach {canonical}"


def _coach_name_key(value: str) -> str:
    return _canonical_coach_name(value).casefold()


def _scheduled_staff_ids(classes: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for remote in classes:
        staff = remote.get("Staff") or remote.get("staff") or {}
        remote_id = _remote_staff_id(staff)
        if remote_id:
            ids.add(remote_id)
    return ids


def _merge_duplicate_coaches(
    db: Session,
    scheduled_remote_ids: set[str] | None = None,
) -> int:
    """Merge safe local aliases such as "Coach Andrea" / "Andrea".

    A group is merged only when it maps to zero or one distinct Mindbody Staff ID.
    Groups with multiple remote IDs or multiple different login accounts are left
    untouched for manual review.
    """
    _ensure_sync_state()
    coaches = list(db.scalars(select(core.Coach).order_by(core.Coach.id)).all())
    if not coaches:
        return 0

    state_rows = db.execute(
        text("SELECT * FROM mindbody_sync_state WHERE entity_type='coach'")
    ).mappings().all()
    state_by_coach = {int(row["entity_id"]): row for row in state_rows if str(row.get("entity_id") or "").isdigit()}

    class_counts = dict(db.execute(
        select(core.ClassSession.coach_id, func.count(core.ClassSession.id))
        .where(core.ClassSession.coach_id.is_not(None))
        .group_by(core.ClassSession.coach_id)
    ).all())

    groups: dict[str, list[core.Coach]] = {}
    for coach in coaches:
        key = _coach_name_key(coach.display_name)
        if key:
            groups.setdefault(key, []).append(coach)

    merged = 0
    for key, rows in groups.items():
        if len(rows) < 2:
            # Normalize even a single provider-prefixed profile for Classy display.
            only = rows[0]
            canonical = _canonical_coach_name(only.display_name)
            if canonical and only.display_name != canonical:
                only.display_name = canonical
            continue

        remote_ids = {
            str((state_by_coach.get(row.id) or {}).get("remote_id") or "")
            for row in rows
            if (state_by_coach.get(row.id) or {}).get("remote_id")
        }
        scheduled_ids = {
            remote_id for remote_id in remote_ids
            if scheduled_remote_ids and remote_id in scheduled_remote_ids
        }
        user_ids = {row.user_id for row in rows if row.user_id}
        if len(scheduled_ids) > 1 or len(user_ids) > 1:
            continue

        primary_remote_id = next(iter(scheduled_ids), None)
        if not primary_remote_id and len(remote_ids) == 1:
            primary_remote_id = next(iter(remote_ids))

        # With no provider identity at all, merge only obvious aliases generated by
        # the historical sync ("Coach X" / "X X"), never arbitrary same-name people.
        if not remote_ids:
            raw_names = [" ".join(str(row.display_name or "").split()) for row in rows]
            obvious_alias = any(
                name.casefold().startswith("coach ")
                or (
                    len(name.split()) == 2
                    and name.split()[0].casefold() == name.split()[1].casefold()
                )
                for name in raw_names
            )
            if not obvious_alias:
                continue

        def score(row: core.Coach) -> tuple[int, int]:
            value = 0
            if row.user_id:
                value += 100000
            if _is_managed_local_photo(row.photo_url):
                value += 20000
            if (row.bio or "").strip():
                value += 5000
            if (state_by_coach.get(row.id) or {}).get("remote_id"):
                value += 2000
            value += int(class_counts.get(row.id, 0)) * 10
            if row.active:
                value += 1
            return value, -row.id

        survivor = max(rows, key=score)
        survivor.display_name = _canonical_coach_name(survivor.display_name) or survivor.display_name

        for duplicate in rows:
            if duplicate.id == survivor.id:
                continue

            dup_state = state_by_coach.get(duplicate.id)
            survivor_state = state_by_coach.get(survivor.id)

            if not survivor.user_id and duplicate.user_id:
                survivor.user_id = duplicate.user_id
            if not _is_managed_local_photo(survivor.photo_url) and _is_managed_local_photo(duplicate.photo_url):
                survivor.photo_url = duplicate.photo_url
            elif not survivor.photo_url and duplicate.photo_url:
                survivor.photo_url = duplicate.photo_url
            if not survivor.bio and duplicate.bio:
                survivor.bio = duplicate.bio
            survivor.active = survivor.active or duplicate.active

            db.execute(
                text("UPDATE classes SET coach_id=:keep WHERE coach_id=:drop"),
                {"keep": survivor.id, "drop": duplicate.id},
            )

            # Remove alias mapping now. The survivor is rebound to the scheduled
            # primary Staff ID after all duplicate rows in this group are removed.
            db.execute(
                text("DELETE FROM mindbody_sync_state WHERE entity_type='coach' AND entity_id=:drop"),
                {"drop": str(duplicate.id)},
            )

            db.delete(duplicate)
            merged += 1

        # Collapse any old alias remote mappings onto the one Staff ID that is
        # actually used by the live/future Mindbody schedule.
        if primary_remote_id:
            primary_state = next(
                (
                    state_by_coach.get(row.id)
                    for row in rows
                    if str((state_by_coach.get(row.id) or {}).get("remote_id") or "") == primary_remote_id
                ),
                None,
            )
            # Delete the survivor state first so the unique remote-ID index can be
            # reassigned cleanly.
            db.execute(
                text("DELETE FROM mindbody_sync_state WHERE entity_type='coach' AND entity_id=:keep"),
                {"keep": str(survivor.id)},
            )
            _state_write(
                db,
                "coach",
                survivor.id,
                remote_id=primary_remote_id,
                local_changed_at=(primary_state or {}).get("local_changed_at"),
                remote_changed_at=(primary_state or {}).get("remote_changed_at"),
                local_hash=_stable_hash(_coach_payload(survivor)),
                remote_hash=(primary_state or {}).get("remote_hash"),
                last_synced_at=(primary_state or {}).get("last_synced_at"),
                sync_error="",
            )
        db.flush()
    return merged


def _deactivate_remote_staff_aliases(
    client: WriteClient,
    all_remote_rows: list[dict[str, Any]],
    scheduled_remote_ids: set[str],
    *,
    max_changes: int = 50,
) -> int:
    """Deactivate duplicate Mindbody Staff aliases that are not used by the schedule.

    A canonical name group is touched only when exactly one Staff ID from that group
    is referenced by live/future classes. That scheduled ID is the primary record;
    other active aliases remain in Mindbody history but are deactivated.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in all_remote_rows:
        remote_id = _remote_staff_id(row)
        payload = _remote_staff_payload(row)
        key = _coach_name_key(payload["display_name"])
        if remote_id and key:
            groups.setdefault(key, []).append(row)

    changed = 0
    for key, rows in groups.items():
        scheduled = [
            row for row in rows
            if _remote_staff_id(row) in scheduled_remote_ids
        ]
        if len(scheduled) != 1:
            continue
        primary_id = _remote_staff_id(scheduled[0])

        for row in rows:
            remote_id = _remote_staff_id(row)
            if not remote_id or remote_id == primary_id:
                continue
            payload = _remote_staff_payload(row)
            if not payload["active"]:
                continue

            # Only clean aliases with the exact fingerprint produced by the old
            # Classy Staff creator: a one-word coach name was sent as both
            # FirstName and LastName, yielding "Andrea Andrea". Do not deactivate
            # arbitrary same-name people; they may be legitimate distinct staff.
            first = str(_value(row, "FirstName", "firstName", default="") or "").strip()
            last = str(_value(row, "LastName", "lastName", default="") or "").strip()
            raw_display = str(_value(row, "DisplayName", "displayName", default="") or "").strip()
            raw_parts = raw_display.split()
            repeated_name = bool(
                (first and last and first.casefold() == last.casefold())
                or (
                    len(raw_parts) == 2
                    and raw_parts[0].casefold() == raw_parts[1].casefold()
                )
            )
            if not repeated_name:
                continue

            if not raw_display:
                raw_display = _mindbody_staff_write_name(payload["display_name"], row)
            client.update_staff(
                remote_id,
                display_name=raw_display,
                bio=payload["bio"],
                active=False,
            )
            changed += 1
            if changed >= max_changes:
                return changed
    return changed


def _refresh_existing_unscheduled_staff_status(
    db: Session,
    all_remote_rows: list[dict[str, Any]],
    scheduled_remote_ids: set[str],
) -> int:
    """Keep existing mapped coaches aligned with Mindbody Active status.

    A coach is not inactive merely because they have no class in the next 45 days.
    We update only already-linked local profiles and never create new unscheduled
    Staff rows here. Explicit Classy edits remain authoritative until synced.
    """
    _ensure_sync_state()
    remote_by_id = {
        _remote_staff_id(row): row
        for row in all_remote_rows
        if _remote_staff_id(row)
    }
    rows = db.execute(
        text("SELECT entity_id, remote_id, local_changed_at FROM mindbody_sync_state WHERE entity_type='coach'")
    ).mappings().all()
    changed = 0
    for state in rows:
        remote_id = str(state.get("remote_id") or "")
        if not remote_id or remote_id in scheduled_remote_ids:
            continue
        remote = remote_by_id.get(remote_id)
        if not remote:
            continue
        try:
            coach = db.get(core.Coach, int(state["entity_id"]))
        except Exception:
            coach = None
        if not coach:
            continue

        # A tracked local edit must not be overwritten by an undated/older remote
        # status. Otherwise mirror Mindbody's actual Active flag.
        remote_modified = _remote_staff_modified(remote)
        local_changed = state.get("local_changed_at")
        if local_changed and (not remote_modified or local_changed > remote_modified):
            continue

        target_active = bool(_remote_staff_payload(remote)["active"])
        if coach.active != target_active:
            coach.active = target_active
            changed += 1
    return changed


def _sync_staff_profiles(
    client: WriteClient,
    db: Session,
    now: datetime,
    *,
    allowed_remote_ids: set[str] | None = None,
) -> tuple[dict[str, int], dict[str, core.Coach]]:
    _ensure_sync_state()
    counts = {
        "staff_remote": 0,
        "staff_created_local": 0,
        "staff_created_remote": 0,
        "staff_pulled": 0,
        "staff_pushed": 0,
        "staff_errors": 0,
        "staff_duplicates_merged": 0,
        "staff_unscheduled_status_updated": 0,
        "staff_remote_aliases_deactivated": 0,
    }
    all_remote_rows = _load_remote_staff(client)
    remote_rows = all_remote_rows

    # Historical alias cleanup is maintenance, not synchronization. Routine sync
    # uses stable Mindbody Staff IDs and never merges people by name.
    counts["staff_duplicates_merged"] = 0

    # The Mindbody Staff endpoint is an employee directory, not a coach roster.
    # Only Staff IDs referenced by live/future classes are allowed to create or
    # update Coach rows in Classy.
    if allowed_remote_ids is not None:
        remote_rows = [row for row in remote_rows if _remote_staff_id(row) in allowed_remote_ids]

    # Defensive dedupe by provider ID in case the API returns overlapping pages.
    unique_remote: dict[str, dict[str, Any]] = {}
    for row in remote_rows:
        remote_id = _remote_staff_id(row)
        if remote_id:
            unique_remote[remote_id] = row
    remote_rows = list(unique_remote.values())

    counts["staff_remote"] = len(remote_rows)

    # Historical remote alias cleanup is intentionally NOT part of the recurring
    # mirror. The duplicate-creation bug is fixed, and automatic deactivation of
    # unscheduled Staff could touch a legitimate same-name employee. Cleanup remains
    # an explicit maintenance operation only.
    counts["staff_remote_aliases_deactivated"] = 0

    locals_ = db.scalars(select(core.Coach)).all()
    state_rows = db.execute(
        text("SELECT * FROM mindbody_sync_state WHERE entity_type='coach'")
    ).mappings().all() if locals_ else []

    local_by_remote: dict[str, core.Coach] = {}
    locals_with_remote: set[int] = set()
    for state in state_rows:
        if state.get("remote_id"):
            try:
                coach = db.get(core.Coach, int(state["entity_id"]))
            except Exception:
                coach = None
            if coach:
                local_by_remote[str(state["remote_id"])] = coach
                locals_with_remote.add(coach.id)

    # Name matching is only a one-time bridge for an old local profile that has
    # never been connected to a Mindbody Staff ID. Once an ID is assigned, that
    # Coach row is never reused for another provider identity.
    unmapped_by_name: dict[str, list[core.Coach]] = {}
    for coach in locals_:
        if coach.id in locals_with_remote:
            continue
        key = _coach_name_key(coach.display_name)
        if key:
            unmapped_by_name.setdefault(key, []).append(coach)

    mapped: dict[str, core.Coach] = {}
    seen_local_ids: set[int] = set()
    for remote in remote_rows:
        remote_id = _remote_staff_id(remote)
        if not remote_id:
            continue
        rp = _remote_staff_payload(remote)
        coach = local_by_remote.get(remote_id)
        if coach is None:
            candidates = unmapped_by_name.get(_coach_name_key(rp["display_name"]), [])
            coach = next((row for row in candidates if row.id not in seen_local_ids), None)
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
        local_by_remote[remote_id] = coach
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
                    display_name=_mindbody_staff_write_name(local_payload["display_name"], remote),
                    bio=local_payload["bio"],
                    active=local_payload["active"],
                )
                returned = result.get("Staff") or result.get("staff")
                if isinstance(returned, dict):
                    rp = _remote_staff_payload(returned)
                    remote_hash = _stable_hash(rp)
                # The successful provider write is now at least as new as the local
                # edit. Advancing remote_changed_at prevents the same Classy edit
                # from being pushed again every 3-minute cycle.
                remote_changed_at = datetime.now(timezone.utc)
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
            canonical_key = _coach_name_key(coach.display_name)
            matches = [
                row for row in all_remote_rows
                if _coach_name_key(_remote_staff_payload(row)["display_name"]) == canonical_key
                and _remote_staff_id(row)
            ]
            unique_matches: dict[str, dict[str, Any]] = {
                _remote_staff_id(row): row for row in matches
            }
            scheduled_matches = {
                remote_id: row
                for remote_id, row in unique_matches.items()
                if allowed_remote_ids and remote_id in allowed_remote_ids
            }
            chosen_matches = scheduled_matches if len(scheduled_matches) == 1 else unique_matches
            if len(chosen_matches) == 1:
                remote_id, remote_match = next(iter(chosen_matches.items()))
                mapped[remote_id] = coach
                coach.display_name = _canonical_coach_name(coach.display_name) or coach.display_name
                _state_write(
                    db, "coach", coach.id,
                    remote_id=remote_id,
                    remote_changed_at=_remote_staff_modified(remote_match) or now,
                    local_hash=_stable_hash(_coach_payload(coach)),
                    remote_hash=_stable_hash(_remote_staff_payload(remote_match)),
                    last_synced_at=now,
                    sync_error="",
                )
                counts["staff_pulled"] += 1
                continue
            if len(unique_matches) > 1:
                raise MindbodyError(
                    f"Ambiguous Mindbody staff alias for {coach.display_name}: "
                    f"{','.join(sorted(unique_matches))}"
                )

            provider_name = _mindbody_staff_write_name(coach.display_name)
            result = client.add_staff(display_name=provider_name, bio=coach.bio or "")
            remote_id = _staff_result_id(result)
            if not remote_id:
                raise MindbodyError("Mindbody staff creation returned no staff ID")
            if not coach.active:
                client.update_staff(
                    remote_id,
                    display_name=provider_name,
                    bio=coach.bio or "",
                    active=False,
                )
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

    if allowed_remote_ids is not None:
        counts["staff_unscheduled_status_updated"] = _refresh_existing_unscheduled_staff_status(
            db,
            all_remote_rows,
            allowed_remote_ids,
        )
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
            if not x.mindbody_class_id
            and abs((core.as_utc(x.starts_at) - starts).total_seconds()) < 90
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


def _apply_remote_class_cancellation(
    db: Session,
    klass: core.ClassSession,
    now: datetime,
) -> list[tuple]:
    """Cancel all local reservations when Mindbody cancels the class instance."""
    email_jobs: list[tuple] = []
    rows = db.scalars(
        select(core.Booking).where(
            core.Booking.class_id == klass.id,
            core.Booking.status == "reserved",
        )
    ).all()
    for booking in rows:
        booking.status = "cancelled"
        booking.mindbody_sync_status = "cancelled_remote"
        booking.mindbody_sync_error = ""
        booking.mindbody_synced_at = now

        if booking.payment_method == "class_credit":
            link = db.get(core.CustomerBookingLink, booking.id)
            profile = db.get(core.CustomerProfile, link.user_id) if link else None
            if profile:
                profile.credits += 1
            booking.payment_method = "class_credit_refunded"

        if booking.email and not booking.email.endswith("@private.invalid"):
            try:
                email_jobs.append(core.cancellation_email_data(booking))
            except Exception:
                pass
    return email_jobs


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
    is_available = _value(remote, "IsAvailable", "isAvailable", default=None)

    changed = False

    # Mindbody is authoritative for physical capacity. Do not keep an older/larger
    # Classy capacity after the provider changed it.
    if remote_capacity is not None and remote_capacity >= 0 and klass.capacity != remote_capacity:
        klass.capacity = remote_capacity
        changed = True

    effective_capacity = remote_capacity if remote_capacity is not None and remote_capacity >= 0 else int(klass.capacity or 0)
    effective_capacity = max(0, int(effective_capacity or 0))
    local_reserved = max(0, int(local_reserved or 0))

    available, target_reserved, imported, normalized_total = compute_public_availability(
        effective_capacity=effective_capacity,
        local_reserved=local_reserved,
        cached_imported=max(0, int(klass.imported_bookings or 0)),
        total_booked=total_booked,
        web_capacity=web_capacity,
        web_booked=web_booked,
        is_available=is_available,
    )

    if int(klass.imported_bookings or 0) != imported:
        klass.imported_bookings = imported
        changed = True

    if normalized_total is not None:
        # GetClasses summary counts can transiently lag the actual roster. Never
        # reopen spots from a lower summary alone after a higher provider-backed
        # occupancy has already been observed. Exact decreases are accepted by
        # _reconcile_class_roster once the roster itself confirms them.
        source_floor = max(
            normalized_total,
            local_reserved,
            max(0, int(klass.source_bookings_total or 0)),
        )
        if int(klass.source_bookings_total or 0) != source_floor:
            klass.source_bookings_total = source_floor
            changed = True
    elif available == 0 and int(klass.source_bookings_total or 0) < target_reserved:
        # Diagnostic aggregate only. Public spots are controlled by imported_bookings.
        klass.source_bookings_total = target_reserved
        changed = True

    return changed


def _reconcile_class_waitlist(
    client: WriteClient,
    db: Session,
    klass: core.ClassSession,
    remote_id: str,
    now: datetime,
) -> dict[str, int]:
    """Mirror one class waitlist by stable Mindbody WaitlistEntryId."""
    result = {"remote": 0, "created": 0, "removed": 0, "unresolved": 0}
    remote_rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        batch = client.get_waitlist_entries(
            class_id=remote_id,
            limit=200,
            offset=offset,
        )
        remote_rows.extend(batch)
        if len(batch) < 200:
            break
        offset += len(batch)

    remote_by_id = {
        _waitlist_entry_id(row): row
        for row in remote_rows
        if _waitlist_entry_id(row)
    }
    result["remote"] = len(remote_by_id)

    local_rows = list(db.scalars(
        select(core.Waitlist).where(core.Waitlist.class_id == klass.id)
    ).all())
    local_by_remote = {
        str(row.mindbody_waitlist_entry_id): row
        for row in local_rows
        if row.mindbody_waitlist_entry_id
    }

    # Remove local entries that Mindbody no longer has (manual removal or promotion).
    for entry_id, local in list(local_by_remote.items()):
        if entry_id in remote_by_id:
            local.mindbody_sync_status = "synced"
            local.mindbody_sync_error = ""
            continue
        db.delete(local)
        result["removed"] += 1

    # Mirror waitlist rows created directly in Mindbody when enough client identity
    # is exposed to do so safely.
    for entry_id, remote in remote_by_id.items():
        if entry_id in local_by_remote:
            continue
        client_data = remote.get("Client") or remote.get("client") or {}
        client_id = _waitlist_client_id(remote)
        email = str(_value(
            remote,
            "ClientEmail", "Email", "email",
            default=_value(client_data, "Email", "email", default=""),
        ) or "").strip().lower()
        first = str(_value(
            remote,
            "ClientFirstName", "FirstName",
            default=_value(client_data, "FirstName", "firstName", default=""),
        ) or "").strip()
        last = str(_value(
            remote,
            "ClientLastName", "LastName",
            default=_value(client_data, "LastName", "lastName", default=""),
        ) or "").strip()

        if not email:
            result["unresolved"] += 1
            continue

        existing = db.scalar(
            select(core.Waitlist).where(
                core.Waitlist.class_id == klass.id,
                func.lower(core.Waitlist.email) == email,
            )
        )
        if existing:
            existing.mindbody_client_id = client_id or existing.mindbody_client_id
            existing.mindbody_waitlist_entry_id = entry_id
            existing.mindbody_sync_status = "synced"
            existing.mindbody_sync_error = ""
            continue

        reference = f"MBW-{entry_id}"[:50]
        row = core.Waitlist(
            class_id=klass.id,
            email=email,
            first_name=first,
            last_name=last,
            reference=reference,
            mindbody_client_id=client_id or None,
            mindbody_waitlist_entry_id=entry_id,
            mindbody_sync_status="synced",
            mindbody_sync_error="",
        )
        db.add(row)
        db.flush()
        user = db.scalar(select(core.User).where(func.lower(core.User.email) == email))
        if user and core.portal_for(user) == "/account":
            if not db.get(core.CustomerWaitlistLink, row.id):
                db.add(core.CustomerWaitlistLink(waitlist_id=row.id, user_id=user.id))
        result["created"] += 1

    db.commit()
    return result


def _reconcile_class_roster(
    client: WriteClient,
    db: Session,
    klass: core.ClassSession,
    remote_id: str,
    now: datetime,
) -> dict[str, int]:
    """Mirror one Mindbody class roster into Classy by stable Visit ID."""
    counts = {"visits": 0, "created": 0, "cancelled": 0, "unresolved": 0}

    payload = client.get_class_visits(remote_id)
    visits = _extract_class_visits(payload)
    active_ids: set[str] = set()
    for visit in visits:
        visit_id = str(_value(visit, "Id", "ID", "VisitId", default="") or "")
        client_data = visit.get("Client") or {}
        client_id = str(_value(
            visit, "ClientId", "ClientID",
            default=_value(client_data, "Id", "ID", default=""),
        ) or "")
        if bool(_value(
            visit,
            "Cancelled", "IsCancelled", "LateCancelled", "EarlyCancelled",
            default=False,
        )):
            continue

        counts["visits"] += 1
        if not visit_id and not client_id:
            # Keep anonymous visits as aggregate occupancy only. A fabricated
            # client::class identity would collide when more than one anonymous
            # visit exists in the same class.
            counts["unresolved"] += 1
            continue
        if not visit_id:
            visit_id = f"client:{client_id}:class:{remote_id}"

        active_ids.add(visit_id)

        booking = db.scalar(
            select(core.Booking).where(core.Booking.mindbody_visit_id == visit_id)
        )
        if booking:
            # A confirmed remove-from-class can remain visible in ClassVisits for a
            # short propagation window. Preserve the local cancellation briefly,
            # but never ignore an active provider Visit forever. If Mindbody still
            # reports the exact Visit ID after the grace period, provider state wins
            # again so occupancy and identity cannot drift permanently.
            if booking.status == "cancelled" and booking.mindbody_sync_status in {
                "cancelled", "cancelled_remote"
            }:
                cancelled_sync_at = core.as_utc(booking.mindbody_synced_at) if booking.mindbody_synced_at else None
                if cancelled_sync_at and now - cancelled_sync_at < timedelta(minutes=5):
                    continue
            booking.status = "reserved"
            booking.mindbody_sync_status = "synced"
            booking.mindbody_sync_error = ""
            booking.mindbody_synced_at = now
            continue

        # Link a website booking/hold before creating a separate external row.
        booking = db.scalar(
            select(core.Booking).where(
                core.Booking.class_id == klass.id,
                core.Booking.source == "website",
                core.Booking.status == "reserved",
                core.Booking.mindbody_client_id == client_id,
            ).order_by(core.Booking.created_at.desc()).limit(1)
        ) if client_id else None
        if booking:
            booking.mindbody_visit_id = visit_id
            booking.mindbody_sync_status = "synced"
            booking.mindbody_sync_error = ""
            booking.mindbody_synced_at = now
            continue

        name = " ".join(
            str(client_data.get(k) or "").strip()
            for k in ("FirstName", "LastName")
        ).strip()
        email = str(
            client_data.get("Email")
            or f"mindbody-{client_id or visit_id}@private.invalid"
        ).lower()
        db.add(core.Booking(
            reference=f"MB-{visit_id}"[:40],
            class_id=klass.id,
            customer_name=name or "Mindbody client",
            email=email,
            phone=str(client_data.get("MobilePhone") or ""),
            status="reserved",
            payment_status="external",
            payment_method="mindbody",
            amount_cents=0,
            source="mindbody",
            mindbody_visit_id=visit_id,
            mindbody_client_id=client_id,
            mindbody_sync_status="synced",
            mindbody_sync_error="",
            mindbody_synced_at=now,
        ))
        counts["created"] += 1

    mirrored = db.scalars(
        select(core.Booking).where(
            core.Booking.class_id == klass.id,
            core.Booking.source == "mindbody",
            core.Booking.status == "reserved",
        )
    ).all()
    for booking in mirrored:
        if booking.mindbody_visit_id not in active_ids:
            booking.status = "cancelled"
            booking.mindbody_sync_status = "cancelled_remote"
            booking.mindbody_sync_error = ""
            booking.mindbody_synced_at = now
            counts["cancelled"] += 1

    local_reserved_after = db.scalar(
        select(func.count(core.Booking.id)).where(
            core.Booking.class_id == klass.id,
            core.Booking.status == "reserved",
        )
    ) or 0

    # The roster is exact identity-level truth. Drop any synthetic occupancy left
    # over from an older summary pass, then rebuild only the synthetic amount still
    # required by the CURRENT public Mindbody class payload (for example a stricter
    # WebCapacity). This prevents a cancelled/promoted visit from being counted once
    # as a real booking and once again through stale imported_bookings.
    klass.imported_bookings = 0
    klass.source_bookings_total = len(active_ids) + int(counts["unresolved"])
    remote = _find_remote_class(client, klass)
    if remote is not None:
        _sync_class_availability(
            db,
            klass,
            remote,
            int(local_reserved_after),
        )

    klass.mindbody_synced_at = now
    db.commit()
    return counts


def reconcile_remote_class(
    remote_class_id: str,
    *,
    start_hint: str | None = None,
    reconcile_roster: bool = True,
    reconcile_waitlist: bool = True,
    sync_coach: bool = False,
) -> dict[str, int | bool]:
    """Refresh one Mindbody class after a webhook event.

    The webhook is only an invalidation signal. Current class metadata, capacity,
    roster, and waitlist truth are re-read from Mindbody so duplicated or
    out-of-order events cannot increment/decrement local counters incorrectly.
    """
    remote_class_id = str(remote_class_id or "").strip()
    if not remote_class_id:
        raise MindbodyError("Missing Mindbody class ID")

    with RECONCILE_LOCK:
        now = datetime.now(timezone.utc)
        client = WriteClient.from_env()
        email_jobs: list[tuple] = []

        with core.SessionLocal() as db:
            klass = db.scalar(
                select(core.ClassSession)
                .where(core.ClassSession.mindbody_class_id == remote_class_id)
                .order_by(core.ClassSession.id.asc())
                .limit(1)
            )

            # A new schedule/class may arrive before the normal mirror has created
            # its local row. Use the canonical fast sync once, then retry the ID
            # lookup instead of inventing a second class from webhook payload data.
            if not klass:
                sync_staff_and_assignments()
                klass = db.scalar(
                    select(core.ClassSession)
                    .where(core.ClassSession.mindbody_class_id == remote_class_id)
                    .order_by(core.ClassSession.id.asc())
                    .limit(1)
                )
                if not klass:
                    return {
                        "found": False,
                        "metadata_updated": 0,
                        "availability_updated": 0,
                        "roster_created": 0,
                        "roster_cancelled": 0,
                        "waitlist_created": 0,
                        "waitlist_removed": 0,
                    }

            remote = None
            hinted_start = _parse_dt(start_hint) if start_hint else None
            if hinted_start:
                payload = client.get_classes(
                    start_date_time=(hinted_start - timedelta(hours=3)).isoformat(),
                    end_date_time=(hinted_start + timedelta(hours=3)).isoformat(),
                    limit=200,
                    offset=0,
                )
                remote = next(
                    (
                        row
                        for row in _extract_list(payload, ("Classes", "classes", "Items"))
                        if isinstance(row, dict)
                        and str(_value(row, "Id", "ID", "ClassId", default="") or "") == remote_class_id
                    ),
                    None,
                )
            if remote is None:
                remote = _find_remote_class(client, klass)

            # A moved class can fall outside the old local time window. One bounded
            # canonical sync is safer than treating "not found in old window" as a
            # cancellation.
            if remote is None:
                sync_staff_and_assignments()
                db.refresh(klass)
                remote = _find_remote_class(client, klass)
            if remote is None:
                raise MindbodyError(f"Mindbody class {remote_class_id} could not be refreshed")

            metadata_updated = int(_sync_remote_class_metadata(klass, remote, now))

            live_reserved = db.scalar(
                select(func.count(core.Booking.id)).where(
                    core.Booking.class_id == klass.id,
                    core.Booking.status == "reserved",
                )
            ) or 0
            availability_updated = int(
                _sync_class_availability(db, klass, remote, int(live_reserved))
            )

            if sync_coach:
                staff_ids = _scheduled_staff_ids([remote])
                _, staff_map = _sync_staff_profiles(
                    client,
                    db,
                    now,
                    allowed_remote_ids=staff_ids,
                )
                _sync_class_coach(client, db, klass, remote, staff_map, now)

            cancelled = _remote_class_cancelled(remote)
            if cancelled:
                email_jobs.extend(_apply_remote_class_cancellation(db, klass, now))

            db.commit()
            local_class_id = klass.id

        roster_counts = {"created": 0, "cancelled": 0, "visits": 0, "unresolved": 0}
        wait_counts = {"created": 0, "removed": 0, "remote": 0, "unresolved": 0}

        if not cancelled and reconcile_roster:
            with core.SessionLocal() as db:
                klass = db.get(core.ClassSession, local_class_id)
                if klass:
                    roster_counts = _reconcile_class_roster(
                        client,
                        db,
                        klass,
                        remote_class_id,
                        now,
                    )

        if not cancelled and reconcile_waitlist:
            with core.SessionLocal() as db:
                klass = db.get(core.ClassSession, local_class_id)
                if klass:
                    wait_counts = _reconcile_class_waitlist(
                        client,
                        db,
                        klass,
                        remote_class_id,
                        now,
                    )

        for email_job in email_jobs:
            try:
                core.send_transactional_email(*email_job)
            except Exception:
                pass

        return {
            "found": True,
            "metadata_updated": metadata_updated,
            "availability_updated": availability_updated,
            "roster_created": int(roster_counts.get("created", 0)),
            "roster_cancelled": int(roster_counts.get("cancelled", 0)),
            "waitlist_created": int(wait_counts.get("created", 0)),
            "waitlist_removed": int(wait_counts.get("removed", 0)),
        }


def sync_rosters_window(*, days: int = 7) -> dict[str, int]:
    """Force identity-level roster reconciliation for a bounded future window."""
    client = WriteClient.from_env()
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=max(1, min(14, int(days))))
    classes: list[dict[str, Any]] = []
    offset = 0
    while True:
        payload = client.get_classes(
            start_date_time=now.isoformat(),
            end_date_time=end.isoformat(),
            limit=200,
            offset=offset,
            public_only=True,
        )
        batch = [
            x for x in _extract_list(payload, ("Classes", "classes", "Items"))
            if isinstance(x, dict)
        ]
        classes.extend(batch)
        if len(batch) < 200:
            break
        offset += len(batch)

    result = {
        "classes_checked": 0,
        "visits": 0,
        "created": 0,
        "cancelled": 0,
        "unresolved": 0,
        "errors": 0,
        "waitlists_checked": 0,
        "waitlist_created": 0,
        "waitlist_removed": 0,
        "waitlist_unresolved": 0,
        "waitlist_errors": 0,
    }
    with core.SessionLocal() as db:
        by_remote = {
            str(row.mindbody_class_id): row
            for row in db.scalars(
                select(core.ClassSession).where(
                    core.ClassSession.mindbody_class_id.is_not(None),
                    core.ClassSession.starts_at >= now,
                    core.ClassSession.starts_at < end,
                )
            ).all()
        }

    for remote in classes:
        remote_id = str(_value(remote, "Id", "ID", "ClassId", default="") or "")
        if not remote_id or _remote_class_cancelled(remote):
            continue
        with core.SessionLocal() as db:
            klass = db.scalar(
                select(core.ClassSession).where(
                    core.ClassSession.mindbody_class_id == remote_id
                )
            )
            if not klass:
                continue
            try:
                counts = _reconcile_class_roster(client, db, klass, remote_id, now)
                result["classes_checked"] += 1
                for key in ("visits", "created", "cancelled", "unresolved"):
                    result[key] += counts[key]
            except Exception:
                db.rollback()
                result["errors"] += 1
                continue

            remote_waitlisted = _value(remote, "TotalWaitlisted", "TotalWaitList", default=0)
            try:
                remote_waitlisted_count = max(0, int(remote_waitlisted or 0))
            except Exception:
                remote_waitlisted_count = 0
            local_waitlisted_count = db.scalar(
                select(func.count(core.Waitlist.id)).where(core.Waitlist.class_id == klass.id)
            ) or 0
            if remote_waitlisted_count or local_waitlisted_count:
                try:
                    wait_counts = _reconcile_class_waitlist(client, db, klass, remote_id, now)
                    result["waitlists_checked"] += 1
                    result["waitlist_created"] += wait_counts["created"]
                    result["waitlist_removed"] += wait_counts["removed"]
                    result["waitlist_unresolved"] += wait_counts["unresolved"]
                except Exception:
                    db.rollback()
                    result["waitlist_errors"] += 1
    return result


def _hide_nonpublic_mindbody_classes(
    db: Session,
    *,
    public_ids: set[str],
    start: datetime,
    end: datetime,
    now: datetime,
) -> int:
    """Hide provider-backed classes that are not in Mindbody's public-visible feed.

    Staff-authenticated GetClasses intentionally exposes hidden/cancelled instances.
    The public website must never keep one of those instances active merely because
    it still exists in Mindbody's staff feed.
    """
    rows = db.scalars(
        select(core.ClassSession).where(
            core.ClassSession.starts_at >= start,
            core.ClassSession.starts_at < end,
            core.ClassSession.status == "active",
            core.ClassSession.mindbody_class_id.is_not(None),
        )
    ).all()
    hidden = 0
    for row in rows:
        remote_id = str(row.mindbody_class_id or "")
        if remote_id and remote_id not in public_ids:
            row.status = "hidden"
            row.mindbody_synced_at = now
            hidden += 1
    return hidden


def sync_cancelled_classes_window(*, days: int = 45) -> dict[str, int]:
    """Apply true Mindbody cancellations without creating hidden phantom classes.

    This uses the staff-authenticated lifecycle feed only to update exact provider
    IDs that already exist locally. It never creates or fuzzy-matches a class.
    """
    client = WriteClient.from_env()
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=2)
    end = now + timedelta(days=max(1, min(45, int(days))))
    rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        payload = client.get_classes(
            start_date_time=start.isoformat(),
            end_date_time=end.isoformat(),
            limit=200,
            offset=offset,
            public_only=False,
        )
        batch = [
            row for row in _extract_list(payload, ("Classes", "classes", "Items"))
            if isinstance(row, dict)
        ]
        rows.extend(batch)
        if len(batch) < 200:
            break
        offset += len(batch)

    counts = {
        "staff_classes_seen": len(rows),
        "cancelled_seen": 0,
        "cancelled_local_updated": 0,
        "cancellation_notifications": 0,
    }
    email_jobs: list[tuple] = []
    with core.SessionLocal() as db:
        for remote in rows:
            if not _remote_class_cancelled(remote):
                continue
            counts["cancelled_seen"] += 1
            remote_id = str(_value(remote, "Id", "ID", "ClassId", default="") or "")
            if not remote_id:
                continue
            klass = db.scalar(
                select(core.ClassSession)
                .where(core.ClassSession.mindbody_class_id == remote_id)
                .limit(1)
            )
            if not klass:
                # Critical invariant: staff-only/cancelled rows never claim a local
                # snapshot row and never create a public class.
                continue
            was_cancelled = klass.status == "cancelled"
            _sync_remote_class_metadata(klass, remote, now)
            if not was_cancelled and klass.status == "cancelled":
                counts["cancelled_local_updated"] += 1
            email_jobs.extend(_apply_remote_class_cancellation(db, klass, now))
        db.commit()

    for email_job in email_jobs:
        try:
            core.send_transactional_email(*email_job)
        except Exception:
            pass
    counts["cancellation_notifications"] = len(email_jobs)
    return counts


def _cancel_unlinked_local_classes(db: Session, *, start: datetime, end: datetime) -> int:
    """Hide local-only sessions inside the live Mindbody window.

    These rows were historically created by the bundled snapshot importer. With
    live Mindbody enabled, an active class in the live window must have a provider
    ID; otherwise it can create phantom availability on the website.
    """
    rows = db.scalars(
        select(core.ClassSession).where(
            core.ClassSession.starts_at >= start,
            core.ClassSession.starts_at < end,
            core.ClassSession.status == "active",
            core.ClassSession.mindbody_class_id.is_(None),
        )
    ).all()
    for row in rows:
        row.status = "cancelled"
        row.mindbody_synced_at = datetime.now(timezone.utc)
    return len(rows)


def sync_schedule_availability_fast() -> dict[str, int]:
    """Prime the public schedule from Mindbody before the API starts serving.

    This deliberately skips staff-directory writes and roster identity reconciliation.
    It updates/creates class instances, cancellation state, and public bookability for
    the full 45-day window so the website never boots with stale spot counts after a
    deployment or process restart.
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
            public_only=True,
        )
        batch = [
            row for row in _extract_list(payload, ("Classes", "classes", "Items"))
            if isinstance(row, dict)
        ]
        classes.extend(batch)
        if len(batch) < 200:
            break
        offset += len(batch)

    public_ids = {
        str(_value(row, "Id", "ID", "ClassId", default="") or "")
        for row in classes
        if str(_value(row, "Id", "ID", "ClassId", default="") or "")
    }
    counts = {
        "classes_seen": len(classes),
        "classes_matched": 0,
        "classes_created_local": 0,
        "classes_skipped_unmapped": 0,
        "metadata_updated": 0,
        "availability_updated": 0,
        "nonpublic_hidden": 0,
        "local_only_cancelled": 0,
    }
    cancellation_email_jobs: list[tuple] = []

    with core.SessionLocal() as db:
        counts["duplicate_classes_merged"] = _dedupe_mindbody_classes(db)
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

        # Staff assignment is intentionally deferred to the normal full mirror.
        # New classes can still be created safely with coach_id=None and are filled
        # in on the next staff reconciliation.
        empty_staff_map: dict[str, core.Coach] = {}
        for remote in classes:
            klass, created_local = _ensure_local_class(
                db, local, remote, empty_staff_map, now
            )
            if not klass:
                counts["classes_skipped_unmapped"] += 1
                continue
            if created_local:
                counts["classes_created_local"] += 1
                reserved_counts.setdefault(klass.id, 0)

            if _sync_remote_class_metadata(klass, remote, now):
                counts["metadata_updated"] += 1

            if _remote_class_cancelled(remote):
                cancellation_email_jobs.extend(
                    _apply_remote_class_cancellation(db, klass, now)
                )

            if _sync_class_availability(
                db,
                klass,
                remote,
                int(reserved_counts.get(klass.id, 0)),
            ):
                counts["availability_updated"] += 1
            counts["classes_matched"] += 1

        counts["nonpublic_hidden"] = _hide_nonpublic_mindbody_classes(
            db, public_ids=public_ids, start=now, end=end, now=now
        )
        counts["local_only_cancelled"] = _cancel_unlinked_local_classes(
            db, start=now, end=end
        )
        db.commit()

    for email_job in cancellation_email_jobs:
        try:
            core.send_transactional_email(*email_job)
        except Exception:
            pass

    counts["remote_class_cancellation_notifications"] = len(
        cancellation_email_jobs
    )
    return counts


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
            public_only=True,
        )
        batch = [x for x in _extract_list(payload, ("Classes", "classes", "Items")) if isinstance(x, dict)]
        classes.extend(batch)
        if len(batch) < 200:
            break
        offset += len(batch)

    public_ids = {
        str(_value(row, "Id", "ID", "ClassId", default="") or "")
        for row in classes
        if str(_value(row, "Id", "ID", "ClassId", default="") or "")
    }
    cancellation_email_jobs: list[tuple] = []
    counts = {
        "classes_seen": len(classes),
        "classes_matched": 0,
        "classes_created_local": 0,
        "classes_skipped_unmapped": 0,
        "metadata_updated": 0,
        "availability_updated": 0,
        "nonpublic_hidden": 0,
        "trainer_assignments_pulled": 0,
        "trainer_assignments_pushed": 0,
        "trainer_assignment_errors": 0,
    }
    with core.SessionLocal() as db:
        counts["duplicate_classes_merged"] = _dedupe_mindbody_classes(db)
        scheduled_staff_ids = _scheduled_staff_ids(classes)
        staff_counts, staff_map = _sync_staff_profiles(
            client, db, now, allowed_remote_ids=scheduled_staff_ids
        )
        counts.update(staff_counts)
        local = db.scalars(
            select(core.ClassSession).where(
                core.ClassSession.starts_at >= now,
                core.ClassSession.starts_at < end,
            )
        ).all()
        local_ids = [row.id for row in local]
        reserved_counts: dict[int, int] = {}
        individual_remote_counts: dict[int, int] = {}
        waitlist_counts: dict[int, int] = {}
        prior_source_totals: dict[int, int] = {
            row.id: int(row.source_bookings_total or 0) for row in local
        }
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
            individual_remote_counts = dict(
                db.execute(
                    select(core.Booking.class_id, func.count(core.Booking.id))
                    .where(
                        core.Booking.class_id.in_(local_ids),
                        core.Booking.status == "reserved",
                        core.Booking.mindbody_visit_id.is_not(None),
                    )
                    .group_by(core.Booking.class_id)
                ).all()
            )
            waitlist_counts = dict(
                db.execute(
                    select(core.Waitlist.class_id, func.count(core.Waitlist.id))
                    .where(core.Waitlist.class_id.in_(local_ids))
                    .group_by(core.Waitlist.class_id)
                ).all()
            )
        roster_candidates: list[tuple[datetime, int, str]] = []
        waitlist_candidates: list[tuple[datetime, int, str]] = []
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
            if _remote_class_cancelled(remote):
                cancellation_email_jobs.extend(
                    _apply_remote_class_cancellation(db, klass, now)
                )
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

            remote_total = _value(remote, "TotalBooked", "TotalClients", default=None)
            remote_id = str(_value(remote, "Id", "ID", "ClassId", default="") or "")
            starts = _parse_dt(_value(remote, "StartDateTime", "startDateTime"))
            try:
                remote_total_int = int(remote_total) if remote_total is not None else None
            except Exception:
                remote_total_int = None
            if (
                remote_id
                and starts
                and remote_total_int is not None
                and int(prior_source_totals.get(klass.id, 0)) != max(0, remote_total_int)
            ):
                roster_candidates.append((starts, klass.id, remote_id))

            remote_waitlisted = _value(remote, "TotalWaitlisted", "TotalWaitList", default=None)
            try:
                remote_waitlisted_int = int(remote_waitlisted) if remote_waitlisted is not None else None
            except Exception:
                remote_waitlisted_int = None
            if (
                remote_id
                and starts
                and remote_waitlisted_int is not None
                and int(waitlist_counts.get(klass.id, 0)) != max(0, remote_waitlisted_int)
            ):
                waitlist_candidates.append((starts, klass.id, remote_id))

        counts["nonpublic_hidden"] = _hide_nonpublic_mindbody_classes(
            db, public_ids=public_ids, start=now, end=end, now=now
        )
        counts["local_only_cancelled"] = _cancel_unlinked_local_classes(db, start=now, end=end)
        db.commit()

    counts["roster_candidates"] = len(roster_candidates)
    counts["rosters_reconciled"] = 0
    counts["roster_rows_created"] = 0
    counts["roster_rows_cancelled"] = 0
    counts["roster_unresolved"] = 0
    counts["roster_errors"] = 0
    counts["waitlist_candidates"] = len(waitlist_candidates)
    counts["waitlists_reconciled"] = 0
    counts["waitlist_rows_created"] = 0
    counts["waitlist_rows_removed"] = 0
    counts["waitlist_unresolved"] = 0
    counts["waitlist_errors"] = 0
    # Bound each fast cycle so a large historical drift cannot starve normal sync.
    for _, class_id, remote_id in sorted(roster_candidates, key=lambda x: x[0])[:50]:
        with core.SessionLocal() as db:
            klass = db.get(core.ClassSession, class_id)
            if not klass:
                continue
            try:
                roster_counts = _reconcile_class_roster(client, db, klass, remote_id, now)
                counts["rosters_reconciled"] += 1
                counts["roster_rows_created"] += roster_counts["created"]
                counts["roster_rows_cancelled"] += roster_counts["cancelled"]
                counts["roster_unresolved"] += roster_counts["unresolved"]
            except Exception:
                db.rollback()
                counts["roster_errors"] += 1

    for _, class_id, remote_id in sorted(waitlist_candidates, key=lambda x: x[0])[:20]:
        with core.SessionLocal() as db:
            klass = db.get(core.ClassSession, class_id)
            if not klass:
                continue
            try:
                wait_counts = _reconcile_class_waitlist(client, db, klass, remote_id, now)
                counts["waitlists_reconciled"] += 1
                counts["waitlist_rows_created"] += wait_counts["created"]
                counts["waitlist_rows_removed"] += wait_counts["removed"]
                counts["waitlist_unresolved"] += wait_counts["unresolved"]
            except Exception:
                db.rollback()
                counts["waitlist_errors"] += 1

    for email_job in cancellation_email_jobs:
        try:
            core.send_transactional_email(*email_job)
        except Exception:
            pass
    counts["remote_class_cancellation_notifications"] = len(cancellation_email_jobs)
    return counts


def sync_from_mindbody() -> dict[str, int]:
    """Run the single canonical Mindbody reconciliation path.

    Historically this function had a second, older implementation that could
    recreate unscheduled Staff rows and refuse capacity decreases. Keeping one
    implementation prevents manual/background sync from disagreeing with the fast
    production mirror.
    """
    return sync_staff_and_assignments()


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
        acquired = False
        try:
            if capability_status()["configured"]:
                acquired = RECONCILE_LOCK.acquire(timeout=20)
                if not acquired:
                    print("Mindbody mirror cycle skipped: reconciliation lock busy", flush=True)
                else:
                    # The frequent mirror owns public schedule/capacity freshness.
                    # Staff/profile maintenance is intentionally kept off this
                    # critical three-minute path.
                    sync_schedule_availability_fast()
                    retry_pending()
        except Exception as exc:
            print(f"Mindbody mirror cycle failed: {type(exc).__name__}: {str(exc)[:300]}", flush=True)
        finally:
            if acquired:
                RECONCILE_LOCK.release()
        time.sleep(SYNC_INTERVAL)


@core.app.on_event("startup")
def start_worker():
    global _worker_started
    if not SYNC_ENABLED or not capability_status()["configured"]:
        return
    with _worker_guard:
        if _worker_started:
            return

        # Initialize the sync-state schema once before any recurring worker can
        # enter it. Failure is bounded by the PostgreSQL lock timeout and can be
        # retried later by the slower maintenance path.
        try:
            _ensure_sync_state()
        except Exception as exc:
            print(
                f"Mindbody sync-state initialization deferred: "
                f"{type(exc).__name__}: {str(exc)[:300]}",
                flush=True,
            )

        # Prime class metadata and public availability synchronously before FastAPI
        # announces startup complete. This removes the historical 180-second stale
        # capacity window after every deploy/restart.
        try:
            with RECONCILE_LOCK:
                prime = sync_schedule_availability_fast()
            print(
                "Mindbody availability prime: "
                f"seen={prime.get('classes_seen', 0)} "
                f"matched={prime.get('classes_matched', 0)} "
                f"created={prime.get('classes_created_local', 0)} "
                f"availability_updated={prime.get('availability_updated', 0)}",
                flush=True,
            )
        except Exception as exc:
            # Keep the cached site online if Mindbody itself is temporarily
            # unreachable. Checkout still performs a strict provider read.
            print(
                f"Mindbody availability prime failed: "
                f"{type(exc).__name__}: {str(exc)[:300]}",
                flush=True,
            )

        _worker_started = True
        threading.Thread(target=_loop, name="mindbody-mirror", daemon=True).start()


def _manual_sync_locked() -> None:
    with RECONCILE_LOCK:
        sync_from_mindbody()
        retry_pending()


@core.app.post("/api/staff/mindbody/sync")
def manual_sync(background: BackgroundTasks, user: core.User = Depends(core.require("bookings.manage"))):
    background.add_task(_manual_sync_locked)
    return {"ok": True, "queued": True}


@core.app.get("/api/staff/mindbody/status")
def mirror_status(user: core.User = Depends(core.require("bookings.view")), db: Session = Depends(core.db_session)):
    failed = db.scalar(select(func.count(core.Booking.id)).where(core.Booking.mindbody_sync_status.in_(["failed", "cancel_failed"]))) or 0
    pending = db.scalar(select(func.count(core.Booking.id)).where(core.Booking.source == "website", core.Booking.mindbody_sync_status == "pending", core.Booking.payment_status == "paid")) or 0
    last = db.scalar(select(func.max(core.ClassSession.mindbody_synced_at)))
    return {**capability_status(), "failed": int(failed), "pending": int(pending), "last_synced_at": last.isoformat() if last else None}
