import os
import threading
from fastapi import Depends, HTTPException
import mindbody_usage
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
            # The provider may say no class visit exists when a prior cancel
            # already succeeded. This is an idempotent success, not a failure.
            if "no class visit found for clientid:" in str(exc).casefold():
                booking.mindbody_sync_status = "cancelled"
                booking.mindbody_sync_error = ""
                booking.mindbody_synced_at = datetime.now(timezone.utc)
            else:
                booking.mindbody_sync_status = "cancel_failed"
                booking.mindbody_sync_error = str(exc)[:1500]
        db.commit()

mindbody_sync.cancel_local_booking = _cancel_local_booking_hardened

_base_retry_pending = mindbody_sync.retry_pending


def _retry_pending_hardened() -> int:
    retried = _base_retry_pending()
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
            public_only=True,
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

        # Remove the provider hold first. Never mark the local booking cancelled
        # unless Mindbody confirmed the reservation is gone.
        try:
            mindbody_sync.cancel_local_booking_strict(booking_id)
        except Exception as exc:
            print(
                f"Stale booking hold release failed: booking_id={booking_id} "
                f"{type(exc).__name__}: {str(exc)[:240]}",
                flush=True,
            )
            continue
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


_retry_pending_before_hold_cleanup = mindbody_sync.retry_pending


def _retry_pending_with_hold_cleanup() -> int:
    retried = _retry_pending_before_hold_cleanup()
    released = _cleanup_stale_booking_holds()
    if released:
        print(f"Released {released} abandoned SumUp booking hold(s)", flush=True)
    return retried


# The three minute mirror loop calls retry_pending() directly, not
# sync_from_mindbody(). Hook cleanup into that hot path so abandoned holds are
# actually released instead of remaining in Mindbody indefinitely.
mindbody_sync.retry_pending = _retry_pending_with_hold_cleanup


@core.app.on_event("startup")
def _cleanup_abandoned_booking_holds_on_startup() -> None:
    try:
        released = _cleanup_stale_booking_holds()
        if released:
            print(f"Startup released {released} abandoned SumUp booking hold(s)", flush=True)
    except Exception as exc:
        print(
            f"Startup booking hold cleanup deferred: {type(exc).__name__}: {str(exc)[:240]}",
            flush=True,
        )


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
ROSTER_SYNC_INTERVAL = max(21600, int(os.getenv("MINDBODY_ROSTER_SYNC_INTERVAL_SECONDS", "86400")))
ROSTER_INITIAL_DELAY = max(0, int(os.getenv("MINDBODY_ROSTER_INITIAL_DELAY_SECONDS", "0")))
ROSTER_WINDOW_DAYS = max(1, min(14, int(os.getenv("MINDBODY_ROSTER_WINDOW_DAYS", "7"))))


def _roster_loop() -> None:
    # Keep the hourly safety sweep near-term so it cannot monopolize the global
    # reconciliation lock. Webhooks own real-time identity updates; a wider roster
    # + staff maintenance pass runs once at startup and then daily.
    if ROSTER_INITIAL_DELAY:
        time.sleep(ROSTER_INITIAL_DELAY)
    cycle = 0
    while True:
        acquired = False
        try:
            # One post-class pass per day; broad future roster checks once a week.
            # Bookings/attendance changes arrive in real time via webhooks.
            full_maintenance = cycle == 0 or cycle % 7 == 0
            acquired = mindbody_sync.RECONCILE_LOCK.acquire(timeout=30)
            if not acquired:
                print("Mindbody roster sweep skipped: reconciliation lock busy", flush=True)
            else:
                completed = mindbody_sync.sync_recent_completed_rosters(lookback_hours=30)
                future = (
                    mindbody_sync.sync_rosters_window(days=ROSTER_WINDOW_DAYS)
                    if full_maintenance else {}
                )
                lifecycle = (
                    mindbody_sync.sync_cancelled_classes_window(days=45)
                    if full_maintenance else {}
                )
                staff = mindbody_sync.sync_staff_and_assignments() if full_maintenance else {}
                print(
                    f"Mindbody roster sweep: completed={completed.get('classes_checked', 0)} "
                    f"future={future.get('classes_checked', 0)} "
                    f"completed_errors={completed.get('errors', 0)} "
                    f"future_errors={future.get('errors', 0)} "
                    f"cancelled_updated={lifecycle.get('cancelled_local_updated', 0)} "
                    f"staff_maintenance={bool(full_maintenance)} "
                    f"staff_errors={staff.get('staff_errors', 0)}",
                    flush=True,
                )
                if completed.get("errors") or future.get("errors"):
                    print(
                        f"Mindbody roster sweep completed with errors: "
                        f"completed={completed} future={future}", flush=True
                    )
        except Exception as exc:
            print(f"Mindbody roster cycle failed: {type(exc).__name__}: {str(exc)[:300]}", flush=True)
        finally:
            if acquired:
                mindbody_sync.RECONCILE_LOCK.release()
        cycle += 1
        time.sleep(ROSTER_SYNC_INTERVAL)


@core.app.on_event("startup")
def _start_roster_worker() -> None:
    global _roster_worker_started
    if (
        not mindbody_sync.SYNC_ENABLED
        or not mindbody_sync.BACKGROUND_SYNC_ENABLED
        or not mindbody_sync.capability_status()["configured"]
    ):
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

# Restrict operational API metrics to authorized booking staff. This is a
# process-local diagnostic, not a substitute for Mindbody partner billing data.
@app.get("/api/staff/mindbody/api-usage")
def mindbody_api_usage(user: core.User = Depends(core.require("bookings.view"))):
    return mindbody_usage.snapshot()



# A Mindbody seat sync is not proof of payment. Finance staff may explicitly
# verify one already-booked visit with one scoped GetClassVisits read. We never
# perform a payment write, class insertion or broad tenant sync from this route.
@app.get("/api/staff/mindbody/prepaid-audit/{booking_id}")
def verify_classy_prepaid_visit(
    booking_id: int,
    user: core.User = Depends(core.require("finance.view")),
    db=Depends(core.db_session),
):
    booking = db.get(core.Booking, booking_id)
    methods = {"class_credit", "hour_pass", "class_pack50"}
    if not booking or booking.source != "website" or booking.payment_method not in methods:
        raise HTTPException(404, "prepaid_booking_not_found")
    if booking.payment_status != "paid":
        return {"booking_id": booking_id, "status": "not_paid_locally"}
    if booking.status != "reserved":
        return {"booking_id": booking_id, "status": "not_active"}
    klass = booking.klass
    class_id = str(klass.mindbody_class_id or "")
    client_id = str(booking.mindbody_client_id or "")
    visit_id = str(booking.mindbody_visit_id or "")
    if not (class_id.isdigit() and client_id and visit_id.isdigit()):
        return {"booking_id": booking_id, "status": "missing_provider_identity"}

    try:
        client = mindbody_sync.WriteClient.from_env(timeout=15.0)
        visits = mindbody_sync._extract_class_visits(client.get_class_visits(class_id))
    except Exception as exc:
        # A read failure is never equivalent to an unpaid provider visit.
        print("Scoped prepaid visit verification failed:",
              type(exc).__name__, flush=True)
        raise HTTPException(503, "mindbody_visit_verification_unavailable") from exc

    matched = [
        visit for visit in visits
        if mindbody_sync._visit_id(visit) == visit_id
        and mindbody_sync._visit_client_id(visit) == client_id
        and not mindbody_sync._visit_is_cancelled(visit)
    ]
    if not matched:
        return {"booking_id": booking_id, "status": "provider_visit_not_found"}
    if len(matched) != 1:
        return {"booking_id": booking_id, "status": "ambiguous_provider_visits"}

    service_name, service_id = mindbody_sync._visit_service_identity(matched[0])
    is_unpaid = service_name.casefold().startswith(("unpaid", "unverrechn"))
    if is_unpaid or not (service_name or service_id):
        status = "provider_unpaid"
    elif service_name or service_id:
        # Another named service exists, but we cannot claim its payment belongs
        # to this Classy credit without a matching purchased entitlement.
        status = "provider_service_attached_needs_entitlement_match"
    else:
        status = "provider_payment_not_verified"
    return {
        "booking_id": booking_id,
        "status": status,
        "payment_method": booking.payment_method,
        "service_name": service_name[:120],
        "service_id_present": bool(service_id),
        "provider_read_only": True,
        "financial_write_performed": False,
    }




# The prepaid settlement lane is intentionally separate from paid SumUp sales.
# It is disabled unless a private Classy Prepaid 0 EUR pricing option exists.
import mindbody_prepaid_settlement as _prepaid_settlement
app.add_event_handler("startup", _prepaid_settlement.start_worker)


@app.get("/api/staff/mindbody/settlement-settings")
def mindbody_settlement_settings(
    user: core.User = Depends(core.require("finance.view")),
):
    return {
        "sumup_recovery": os.getenv("MINDBODY_PAYMENT_RECOVERY_ENABLED", "true").lower() in
            {"true", "1", "yes", "on"},
        "classy_prepaid_service_configured": _prepaid_settlement.configured(),
        "classy_prepaid_auto_settlement_enabled": _prepaid_settlement.enabled(),
        "classy_prepaid_requires_private_zero_eur_service": True,
    }


@app.post("/api/staff/mindbody/reconcile-prepaid/{booking_id}")
def reconcile_one_prepaid_booking(
    booking_id: int,
    user: core.User = Depends(core.require("bookings.manage")),
):
    if not core.can(user, "finance.view"):
        raise HTTPException(403, "finance_permission_required")
    return _prepaid_settlement.settle_prepaid_visit(booking_id)


@app.post("/api/staff/mindbody/verify-prepaid/{booking_id}")
def verify_one_prepaid_booking(
    booking_id: int,
    user: core.User = Depends(core.require("bookings.manage")),
):
    if not core.can(user, "finance.view"):
        raise HTTPException(403, "finance_permission_required")
    try:
        return _prepaid_settlement.confirm_existing_prepaid_visit(booking_id)
    except Exception as exc:
        raise HTTPException(503, "mindbody_provider_verification_unavailable") from exc


@app.post("/api/staff/mindbody/retry-sumup/{order_id}")
def retry_verified_sumup_pricing_blocker(
    order_id: int,
    user: core.User = Depends(core.require("bookings.manage")),
):
    """Finance-approved retry ONLY when the prior attempt never posted a sale.

    In particular an unknown provider response, duplicate visit, or manual
    accounting issue must not be converted into a fresh checkout attempt.
    """
    if not core.can(user, "finance.view"):
        raise HTTPException(403, "finance_permission_required")
    from sqlalchemy import select as sa_select
    with core.SessionLocal() as db:
        order = db.scalar(
            sa_select(core.PaymentOrder)
            .where(core.PaymentOrder.id == order_id).with_for_update()
        )
        booking = db.scalar(
            sa_select(core.Booking)
            .where(core.Booking.reference == order.booking_reference)
            .with_for_update()
        ) if order and order.booking_reference else None
        if (
            not order or not booking
            or order.provider != "sumup"
            or order.status != "paid"
            or not order.provider_payment_id
            or order.mindbody_sale_status != "manual_review"
            or order.mindbody_sale_error != "pricing_option_not_enabled_for_class"
            or booking.source != "website"
            or booking.status != "reserved"
            or booking.payment_method != "sumup"
            or booking.payment_status != "paid"
            or not booking.klass.mindbody_class_id
            or int(booking.amount_cents or 0) <= 0
        ):
            raise HTTPException(409, "sumup_retry_requires_verified_pricing_blocker")
        checkout_id = str(order.provider_payment_id)
        amount_cents = int(order.amount_cents or 0)

    # Read the ORIGINAL SumUp checkout again. Never trust a local paid flag alone.
    # External I/O is outside a DB transaction.
    try:
        provider = feedback._sumup_request(f"/v0.1/checkouts/{checkout_id}")
        verified = (
            str(provider.get("id") or "") == checkout_id
            and str(provider.get("status") or "").upper() == "PAID"
            and str(provider.get("currency") or "").upper() == "EUR"
            and str(provider.get("merchant_code") or "") == os.getenv("SUMUPMERCHANT", "")
            and feedback._sumup_amount_cents(provider) == amount_cents
        )
    except Exception as exc:
        print("Finance SumUp provider recheck failed:", type(exc).__name__, flush=True)
        raise HTTPException(503, "sumup_provider_verification_unavailable") from exc
    if not verified:
        raise HTTPException(409, "sumup_original_charge_not_verified")

    # Reset only this uniquely safe pre-check blocker. Unknown provider writes
    # stay in manual_review and can never be turned into repeatable sales.
    with core.SessionLocal() as db:
        order = db.scalar(
            sa_select(core.PaymentOrder)
            .where(core.PaymentOrder.id == order_id).with_for_update()
        )
        if (not order or order.mindbody_sale_status != "manual_review"
                or order.mindbody_sale_error != "pricing_option_not_enabled_for_class"):
            raise HTTPException(409, "sumup_retry_state_changed")
        order.mindbody_sale_status = "pending"
        order.mindbody_sale_error = ""
        db.commit()

    success = mindbody_sync.reconcile_paid_booking_sale(order_id)
    with core.SessionLocal() as db:
        order = db.get(core.PaymentOrder, order_id)
        return {
            "order_id": order_id,
            "provider_payment_confirmed": True,
            "mindbody_sale_verified": bool(success),
            "mindbody_sale_status": str(order.mindbody_sale_status) if order else "unknown",
            "financial_review_required": not success,
        }


# Reconcile only confirmed SumUp-paid orders which are still unresolved in
# Mindbody. Runs entirely from local SQL when idle and never restarts bulk sync.
from mindbody_paid_recovery import start_worker as _start_paid_sale_recovery
app.add_event_handler("startup", _start_paid_sale_recovery)


def _repair_confirmed_absent_cancellations_on_startup() -> None:
    """Clear stale failures only when Mindbody explicitly reported no visit.

    This touches local database rows only. It does not change refunds,
    payments, or submit additional provider requests.
    """
    from sqlalchemy import text
    with core.engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE bookings
               SET mindbody_sync_status='cancelled',
                   mindbody_sync_error='',
                   mindbody_synced_at=now()
             WHERE source='website'
               AND status='cancelled'
               AND mindbody_sync_status='cancel_failed'
               AND lower(mindbody_sync_error) LIKE 'no class visit found for clientid:%'
        """))
        if result.rowcount:
            print(f"Confirmed absent Mindbody cancellation repaired locally: {result.rowcount}", flush=True)


app.add_event_handler("startup", _repair_confirmed_absent_cancellations_on_startup)
