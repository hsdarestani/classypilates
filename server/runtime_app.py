import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import joinedload

import feedback_app as feedback
import class_language  # registers DE/EN class-language routes and payloads
import mindbody_sync  # registers the production two-way booking mirror

app = feedback.app
core = mindbody_sync.core


# Mindbody v6 requires the issued user token in the HTTP Authorization header as
# "Bearer <token>". Keep the token normalization at the integration boundary so
# every authenticated GET/POST in WriteClient uses the same correct form.
_original_issue_token = mindbody_sync.WriteClient.issue_token


def _issue_bearer_token(self) -> str:
    token = _original_issue_token(self)
    if token and not token.lower().startswith("bearer "):
        self.access_token = f"Bearer {token}"
    return self.access_token


mindbody_sync.WriteClient.issue_token = _issue_bearer_token


# We own customer-facing transactional mail, so prevent Mindbody from emitting a
# second generic class confirmation for website-origin bookings.
def _add_to_class_without_provider_email(self, client_id: str, class_id: str):
    return self._write(
        "class/addclienttoclass",
        {
            "ClientId": client_id,
            "ClassId": int(class_id),
            "RequirePayment": False,
            "SendEmail": False,
        },
    )


mindbody_sync.WriteClient.add_to_class = _add_to_class_without_provider_email


# Mindbody can expose a cancelled roster entry through cancellation flags or the
# visit Status. Normalize all known forms so cancelled reservations never keep a
# local spot occupied.
_original_value = mindbody_sync._value


def _mindbody_value(row: dict, *names: str, default=None):
    value = _original_value(row, *names, default=None)
    if value is not None:
        return value
    if any(name in {"Cancelled", "IsCancelled"} for name in names):
        flags = [
            row.get(key)
            for key in ("LateCancelled", "lateCancelled", "EarlyCancelled", "earlyCancelled")
            if row.get(key) is not None
        ]
        if any(bool(flag) for flag in flags):
            return True
        status = str(row.get("Status") or row.get("status") or "").strip().casefold()
        if status == "cancelled":
            return True
        if flags:
            return False
    return default


mindbody_sync._value = _mindbody_value


# Use VisitId when Mindbody returned one so a website cancellation removes the
# exact mirrored visit. Failed upstream cancellations remain retryable.
def _cancel_local_booking_hardened(booking_id: int) -> None:
    with core.SessionLocal() as db:
        booking = db.scalar(
            select(core.Booking)
            .options(joinedload(core.Booking.klass))
            .where(core.Booking.id == booking_id)
            .with_for_update()
        )
        if (
            not booking
            or booking.source != "website"
            or not booking.mindbody_client_id
            or not booking.klass.mindbody_class_id
        ):
            return
        try:
            payload = {
                "ClientId": booking.mindbody_client_id,
                "ClassId": int(booking.klass.mindbody_class_id),
                "LateCancel": False,
            }
            visit_id = str(booking.mindbody_visit_id or "").strip()
            if visit_id.isdigit():
                payload["VisitId"] = int(visit_id)
            mindbody_sync.WriteClient.from_env()._write("class/removeclientfromclass", payload)
            booking.mindbody_sync_status = "cancelled"
            booking.mindbody_sync_error = ""
            booking.mindbody_synced_at = datetime.now(timezone.utc)
        except Exception as exc:
            booking.mindbody_sync_status = "cancel_failed"
            booking.mindbody_sync_error = str(exc)[:1500]
        db.commit()


mindbody_sync.cancel_local_booking = _cancel_local_booking_hardened

_original_retry_pending = mindbody_sync.retry_pending


def _retry_pending_hardened() -> int:
    retried = _original_retry_pending()
    with core.SessionLocal() as db:
        cancellation_ids = list(
            db.scalars(
                select(core.Booking.id)
                .where(
                    core.Booking.source == "website",
                    core.Booking.status == "cancelled",
                    core.Booking.mindbody_sync_status == "cancel_failed",
                )
                .limit(100)
            )
        )
    for booking_id in cancellation_ids:
        mindbody_sync.cancel_local_booking(booking_id)
    return retried + len(cancellation_ids)


mindbody_sync.retry_pending = _retry_pending_hardened


# A booking created on this website can later be cancelled by staff directly in
# Mindbody. The base mirror already pulls Mindbody-origin bookings; this second
# reconciliation closes the loop for website-origin bookings that were pushed to
# Mindbody and subsequently disappear from the active Mindbody roster.
_original_sync_from_mindbody = mindbody_sync.sync_from_mindbody


def _visit_value(row: dict, *names: str, default=None):
    for name in names:
        if row.get(name) is not None:
            return row[name]
    return default


def _is_cancelled_visit(visit: dict) -> bool:
    flags = [
        visit.get(key)
        for key in (
            "Cancelled",
            "IsCancelled",
            "LateCancelled",
            "lateCancelled",
            "EarlyCancelled",
            "earlyCancelled",
        )
        if visit.get(key) is not None
    ]
    if any(bool(flag) for flag in flags):
        return True
    return str(visit.get("Status") or visit.get("status") or "").strip().casefold() == "cancelled"


def _reconcile_remote_website_cancellations() -> int:
    now = datetime.now(timezone.utc)
    email_jobs = []
    cancelled = 0
    with core.SessionLocal() as db:
        rows = db.scalars(
            select(core.Booking)
            .join(core.ClassSession, core.Booking.class_id == core.ClassSession.id)
            .options(joinedload(core.Booking.klass).joinedload(core.ClassSession.studio))
            .where(
                core.Booking.source == "website",
                core.Booking.status == "reserved",
                core.Booking.payment_status == "paid",
                core.Booking.mindbody_sync_status == "synced",
                core.Booking.mindbody_visit_id.is_not(None),
                core.ClassSession.starts_at >= now - timedelta(hours=2),
            )
        ).all()
        by_class = defaultdict(list)
        for booking in rows:
            if booking.klass.mindbody_class_id:
                by_class[str(booking.klass.mindbody_class_id)].append(booking)
        if not by_class:
            return 0

        client = mindbody_sync.WriteClient.from_env()
        for mindbody_class_id, bookings in by_class.items():
            try:
                payload = client.get_class_visits(mindbody_class_id)
            except mindbody_sync.MindbodyError:
                # Never infer cancellations when the upstream roster cannot be read.
                continue
            visits = [
                item
                for item in mindbody_sync._extract_list(payload, ("Visits", "visits", "ClassVisits", "Items"))
                if isinstance(item, dict)
            ]
            active_visit_ids: set[str] = set()
            active_client_ids: set[str] = set()
            for visit in visits:
                if _is_cancelled_visit(visit):
                    continue
                client_data = visit.get("Client") or visit.get("client") or {}
                client_id = str(
                    _visit_value(
                        visit,
                        "ClientId",
                        "ClientID",
                        default=_visit_value(client_data, "Id", "ID", default=""),
                    )
                    or ""
                )
                visit_id = str(_visit_value(visit, "Id", "ID", "VisitId", "VisitID", default="") or "")
                if visit_id:
                    active_visit_ids.add(visit_id)
                if client_id:
                    active_client_ids.add(client_id)

            for booking in bookings:
                visit_still_active = str(booking.mindbody_visit_id or "") in active_visit_ids
                client_still_active = bool(booking.mindbody_client_id) and str(booking.mindbody_client_id) in active_client_ids
                if visit_still_active or client_still_active:
                    continue

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
                email_jobs.append(core.cancellation_email_data(booking))
                cancelled += 1
        db.commit()

    for email_job in email_jobs:
        core.send_transactional_email(*email_job)
    return cancelled


def _sync_from_mindbody_hardened() -> dict[str, int]:
    counts = _original_sync_from_mindbody()
    counts["remote_website_cancelled"] = _reconcile_remote_website_cancellations()
    return counts


mindbody_sync.sync_from_mindbody = _sync_from_mindbody_hardened


def _prefer_latest_routes() -> None:
    """Keep the newest handler when transitional modules register the same route.

    main.py still contains the legacy booking/class handlers while feedback_app.py
    registers their production V2 replacements on the same FastAPI instance. Starlette
    matches routes in registration order, so without this normalization the legacy
    handler can shadow the newer SumUp/Mindbody-aware implementation.
    """
    seen: set[tuple[str, frozenset[str]]] = set()
    kept = []
    for route in reversed(app.router.routes):
        path = getattr(route, "path", None)
        methods = frozenset(getattr(route, "methods", set()) or set())
        if not path or not methods:
            kept.append(route)
            continue
        key = (path, methods)
        if key in seen:
            continue
        seen.add(key)
        kept.append(route)
    app.router.routes[:] = list(reversed(kept))


def _assert_production_booking_route() -> None:
    matches = [
        route
        for route in app.router.routes
        if getattr(route, "path", None) == "/api/bookings"
        and "POST" in (getattr(route, "methods", set()) or set())
    ]
    if len(matches) != 1 or getattr(matches[0].endpoint, "__name__", "") != "public_booking_v2":
        raise RuntimeError("Production /api/bookings route is not the SumUp/Mindbody-aware V2 handler")


_prefer_latest_routes()
_assert_production_booking_route()


@app.get('/api/capabilities')
def capabilities():
    return {
        'ok': True,
        'instant_email_notifications': bool(os.getenv('SMTP_HOST')),
        'branded_html_email': True,
        'sepa_provider_credentials': bool(os.getenv('SEPA_PROVIDER_KEY')),
        'booking_languages': ['de', 'en'],
        'class_languages': ['de', 'en'],
        'credit_packs': [1, 5, 10, 20, 30, 50],
        'class_recurrence': 'monthly',
        'monthly_memberships': True,
        'mindbody_mirror': mindbody_sync.capability_status(),
    }
