import os
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

import feedback_app as feedback
import class_language  # registers DE/EN class-language routes and payloads
import mindbody_sync  # registers the production two-way booking mirror
import mindbody_webhooks

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
def _add_to_class_without_provider_email(
    self,
    client_id: str,
    class_id: str,
    *,
    waitlist: bool = False,
):
    return self._write(
        "class/addclienttoclass",
        {
            "ClientId": client_id,
            "ClassId": int(class_id),
            "RequirePayment": False,
            "Waitlist": bool(waitlist),
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
            .where(core.Booking.id == booking_id)
            .with_for_update()
        )
        if not booking or booking.source != "website":
            return
        if not booking.mindbody_client_id or not booking.klass.mindbody_class_id:
            booking.mindbody_sync_status = "cancelled"
            booking.mindbody_sync_error = ""
            booking.mindbody_synced_at = datetime.now(timezone.utc)
            db.commit()
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


def _as_int(row: dict, *names: str):
    value = _visit_value(row, *names, default=None)
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None


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
                core.Booking.payment_status.in_(["paid", "pending"]),
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
            visits = mindbody_sync._extract_class_visits(payload)
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
                booking_visit_id = str(booking.mindbody_visit_id or "").strip()
                booking_client_id = str(booking.mindbody_client_id or "").strip()
                if booking_visit_id:
                    still_active = booking_visit_id in active_visit_ids
                else:
                    still_active = bool(booking_client_id) and booking_client_id in active_client_ids
                if still_active:
                    continue

                was_paid = booking.payment_status == "paid"
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

                # A pending SumUp checkout must not remain payable after Mindbody
                # removed its seat. Deactivate it immediately when possible. If
                # provider state is temporarily unavailable, keep payment_status
                # pending; the payment synchronizer is hardened not to revive this
                # cancelled booking if a late payment arrives.
                if booking.payment_status == "pending" and booking.payment_method == "sumup":
                    order = db.scalar(
                        select(core.PaymentOrder)
                        .where(core.PaymentOrder.booking_reference == booking.reference)
                        .order_by(core.PaymentOrder.created_at.desc())
                        .limit(1)
                    )
                    if order and order.status == "pending" and order.provider_payment_id:
                        try:
                            feedback._sumup_request(
                                f"/v0.1/checkouts/{order.provider_payment_id}",
                                method="DELETE",
                            )
                            order.status = "cancelled"
                            booking.payment_status = "cancelled"
                        except Exception:
                            pass

                if was_paid:
                    email_jobs.append(core.cancellation_email_data(booking))
                cancelled += 1
        db.commit()

    for email_job in email_jobs:
        core.send_transactional_email(*email_job)
    return cancelled


def _reconcile_mindbody_availability() -> int:
    """Make Mindbody the source of truth for public bookable spots.

    The historical importer may have stored a larger local capacity. The base mirror
    used max(local, remote), which meant a later lower Mindbody capacity could never
    reduce the website capacity. Reconcile the next two weeks from the live Mindbody
    class payload and add only the synthetic occupancy needed to reproduce Mindbody's
    actual public availability.
    """
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=15)
    client = mindbody_sync.WriteClient.from_env()
    remote_classes: list[dict] = []
    offset = 0
    while True:
        payload = client.get_classes(
            start_date_time=now.isoformat(),
            end_date_time=end.isoformat(),
            limit=200,
            offset=offset,
        )
        batch = [
            item
            for item in mindbody_sync._extract_list(payload, ("Classes", "classes", "Items"))
            if isinstance(item, dict)
        ]
        remote_classes.extend(batch)
        if len(batch) < 200:
            break
        offset += len(batch)

    corrected = 0
    with core.SessionLocal() as db:
        local_rows = db.scalars(
            select(core.ClassSession).where(
                core.ClassSession.starts_at >= now,
                core.ClassSession.starts_at < end,
                core.ClassSession.mindbody_class_id.is_not(None),
            )
        ).all()
        by_remote_id = {str(row.mindbody_class_id): row for row in local_rows if row.mindbody_class_id}
        class_ids = [row.id for row in local_rows]
        live_counts = {}
        if class_ids:
            live_counts = dict(
                db.execute(
                    select(core.Booking.class_id, func.count(core.Booking.id))
                    .where(
                        core.Booking.class_id.in_(class_ids),
                        core.Booking.status == "reserved",
                    )
                    .group_by(core.Booking.class_id)
                ).all()
            )

        for remote in remote_classes:
            remote_id = str(_visit_value(remote, "Id", "ID", "ClassId", default="") or "")
            klass = by_remote_id.get(remote_id)
            if not klass:
                continue

            remote_capacity = _as_int(remote, "MaxCapacity", "Capacity")
            if remote_capacity is None or remote_capacity < 0:
                continue

            total_booked = _as_int(remote, "TotalBooked", "TotalClients")
            web_capacity = _as_int(remote, "WebCapacity")
            total_web_booked = _as_int(remote, "TotalWebBooked")

            # Always accept Mindbody capacity exactly; never preserve an older,
            # larger local/imported capacity.
            klass.capacity = remote_capacity

            if total_booked is not None:
                physical_available = max(0, remote_capacity - max(0, total_booked))
                available = physical_available
                if web_capacity is not None and total_web_booked is not None:
                    web_available = max(0, web_capacity - max(0, total_web_booked))
                    available = min(available, web_available)

                target_reserved = max(0, remote_capacity - available)
                local_reserved = int(live_counts.get(klass.id, 0))
                # imported_bookings acts as a non-PII occupancy remainder so the
                # public API exposes the same number of spots as Mindbody even if
                # a roster row is temporarily unavailable to this integration.
                klass.imported_bookings = max(0, target_reserved - local_reserved)
                klass.source_bookings_total = max(0, total_booked)

            klass.mindbody_synced_at = now
            corrected += 1

        db.commit()
    return corrected


PENDING_HOLD_TTL_SECONDS = max(900, int(os.getenv("MINDBODY_PENDING_HOLD_TTL_SECONDS", "1800")))


def _cleanup_stale_booking_holds() -> int:
    """Release Mindbody holds for abandoned SumUp bookings after verifying payment."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=PENDING_HOLD_TTL_SECONDS)
    released = 0

    with core.SessionLocal() as db:
        stale_ids = list(db.scalars(
            select(core.Booking.id).where(
                core.Booking.source == "website",
                core.Booking.status == "reserved",
                core.Booking.payment_status == "pending",
                core.Booking.payment_method == "sumup",
                core.Booking.created_at < cutoff,
            ).limit(100)
        ))

    for booking_id in stale_ids:
        should_cancel = False
        with core.SessionLocal() as db:
            booking = db.get(core.Booking, booking_id)
            if not booking or booking.status != "reserved" or booking.payment_status != "pending":
                continue
            order = db.scalar(
                select(core.PaymentOrder)
                .where(core.PaymentOrder.booking_reference == booking.reference)
                .order_by(core.PaymentOrder.created_at.desc())
                .limit(1)
            )
            if order and order.status == "paid":
                continue
            if order and order.provider_payment_id:
                try:
                    checkout = feedback._sumup_request(f"/v0.1/checkouts/{order.provider_payment_id}")
                    synced = feedback._sync_sumup_order(checkout, db, None)
                    if synced and synced.status == "paid":
                        continue
                    if synced and synced.status in {"failed", "cancelled"}:
                        should_cancel = True
                    elif synced and synced.status == "pending":
                        # Never release a Mindbody seat while a SumUp checkout can
                        # still become paid. Deactivate the checkout first; only a
                        # successful provider-side deactivation makes the hold safe
                        # to release.
                        try:
                            feedback._sumup_request(
                                f"/v0.1/checkouts/{order.provider_payment_id}",
                                method="DELETE",
                            )
                            order.status = "cancelled"
                            db.commit()
                            should_cancel = True
                        except Exception:
                            # Payment may have raced the deactivation. Re-read the
                            # provider state and keep the seat unless cancellation is
                            # certain.
                            try:
                                latest = feedback._sumup_request(f"/v0.1/checkouts/{order.provider_payment_id}")
                                latest_order = feedback._sync_sumup_order(latest, db, None)
                                if latest_order and latest_order.status == "paid":
                                    continue
                                if latest_order and latest_order.status in {"failed", "cancelled"}:
                                    should_cancel = True
                                else:
                                    continue
                            except Exception:
                                continue
                except Exception:
                    # Never release a hold when payment state cannot be verified.
                    continue
            else:
                should_cancel = True

        if not should_cancel:
            continue

        # Remove provider hold first; if that fails, leave a retryable cancel_failed marker.
        mindbody_sync.cancel_local_booking(booking_id)
        with core.SessionLocal() as db:
            booking = db.get(core.Booking, booking_id)
            if not booking or booking.payment_status == "paid":
                continue
            booking.status = "cancelled"
            booking.payment_status = "cancelled"
            if booking.mindbody_sync_status != "cancelled":
                booking.mindbody_sync_status = "cancel_failed"
            order = db.scalar(
                select(core.PaymentOrder)
                .where(core.PaymentOrder.booking_reference == booking.reference)
                .order_by(core.PaymentOrder.created_at.desc())
                .limit(1)
            )
            if order and order.status != "paid":
                order.status = "cancelled"
            db.commit()
            released += 1
    return released


def _sync_from_mindbody_hardened() -> dict[str, int]:
    thread_name = threading.current_thread().name

    # Deployment checks and the frequent mirror worker must stay fast. The fast
    # reconciliation now includes class capacity + booked-space availability,
    # staff profiles and trainer assignments.
    if thread_name in {"MainThread", "mindbody-mirror"}:
        counts = mindbody_sync.sync_staff_and_assignments()
        if thread_name == "mindbody-mirror":
            counts["remote_website_cancelled"] = _reconcile_remote_website_cancellations()
            counts["stale_booking_holds_released"] = _cleanup_stale_booking_holds()
        return counts

    # Explicit/full roster jobs still mirror individual Mindbody visits and then
    # reconcile availability/cancellations as a safety net.
    counts = _original_sync_from_mindbody()
    counts["remote_website_cancelled"] = _reconcile_remote_website_cancellations()
    counts["availability_corrected"] = _reconcile_mindbody_availability()
    return counts


mindbody_sync.sync_from_mindbody = _sync_from_mindbody_hardened


_roster_worker_started = False
_roster_worker_guard = threading.Lock()
ROSTER_SYNC_INTERVAL = max(900, int(os.getenv("MINDBODY_ROSTER_SYNC_INTERVAL_SECONDS", "3600")))
ROSTER_INITIAL_DELAY = max(0, int(os.getenv("MINDBODY_ROSTER_INITIAL_DELAY_SECONDS", "0")))
ROSTER_WINDOW_DAYS = max(1, min(14, int(os.getenv("MINDBODY_ROSTER_WINDOW_DAYS", "7"))))


def _roster_loop() -> None:
    # Reconcile today's/next-24h rosters immediately after startup without blocking
    # API readiness. This is the high-value window for campaign traffic and exact
    # spot counts. Later sweeps cover the wider configured horizon hourly.
    if ROSTER_INITIAL_DELAY:
        time.sleep(ROSTER_INITIAL_DELAY)
    first_pass = True
    while True:
        try:
            days = 1 if first_pass else ROSTER_WINDOW_DAYS
            with mindbody_sync.RECONCILE_LOCK:
                result = mindbody_sync.sync_rosters_window(days=days)
            print(
                f"Mindbody roster sweep: days={days} classes={result.get('classes_checked', 0)} "
                f"visits={result.get('visits', 0)} errors={result.get('errors', 0)}",
                flush=True,
            )
            if result.get("errors"):
                print(f"Mindbody roster sweep completed with errors: {result}", flush=True)
        except Exception as exc:
            print(f"Mindbody roster cycle failed: {type(exc).__name__}: {str(exc)[:300]}", flush=True)
        first_pass = False
        time.sleep(ROSTER_SYNC_INTERVAL)


@core.app.on_event("startup")
def _start_roster_worker() -> None:
    global _roster_worker_started
    if not mindbody_sync.SYNC_ENABLED or not mindbody_sync.capability_status()["configured"]:
        return
    with _roster_worker_guard:
        if _roster_worker_started:
            return
        _roster_worker_started = True
        threading.Thread(target=_roster_loop, name="mindbody-roster", daemon=True).start()


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
mindbody_webhooks.install(app)


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
        'mindbody_webhook': mindbody_webhooks.webhook_status(),
    }
