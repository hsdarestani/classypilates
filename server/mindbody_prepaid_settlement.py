"""Safe Classy prepaid-credit -> Mindbody settlement.

Classy credit debits and hour/50-course usage are already recorded atomically
when the local booking is created. They must NOT become a second 28 EUR sale.
This worker attaches exactly one explicitly configured, zero-priced private
Mindbody 'Classy Prepaid' service to the same VisitId.

A missing service configuration is a blocker, not permission to use ClassPass,
Wellpass, another client's pricing option, or a fallback billable service.
Never retry an uncertain provider POST automatically.
"""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text

import main as core
import mindbody_sync as mb

PREPAID_METHODS = {"class_credit", "hour_pass", "class_pack50"}
PRIVATE_SERVICE_NAMES = {"classy prepaid", "classy website prepaid"}
DAILY_LIMIT = 8
CHECK_INTERVAL_SECONDS = 900
_started = False
_worker_lock = threading.Lock()

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS mindbody_prepaid_settlements (
    booking_id INTEGER PRIMARY KEY REFERENCES bookings(id),
    status VARCHAR(32) NOT NULL DEFAULT 'checking',
    service_id VARCHAR(80),
    error TEXT NOT NULL DEFAULT '',
    attempts INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


def configured() -> bool:
    return bool(
        os.getenv("MINDBODY_CLASSY_PREPAID_SERVICE_ID", "").strip().isdigit()
        and mb.SYNC_ENABLED
        and mb.capability_status()["configured"]
    )


def enabled() -> bool:
    return (
        configured()
        and os.getenv("MINDBODY_CLASSY_PREPAID_SETTLEMENT_ENABLED", "false").lower()
        in {"1", "true", "yes", "on"}
    )


def eligible_prepaid_service(rows: list[dict], service_id: str) -> dict:
    """Select one explicit, zero-value, private Classy-owned service. Pure."""
    matches = []
    for row in rows:
        rid = str(mb._value(row, "Id", "ID", "ProductId", default="") or "")
        name = " ".join(str(mb._value(row, "Name", "name", default="")).split()).casefold()
        price = mb._service_price_cents(row)
        try:
            count = int(mb._value(row, "Count", "count", default=0) or 0)
        except (ValueError, TypeError):
            count = 0
        kind = str(mb._value(row, "Type", "type", default="")).casefold()
        if (
            rid == str(service_id)
            and name in PRIVATE_SERVICE_NAMES
            and price == 0
            and count == 1
            and kind in {"dropin", ""}
        ):
            matches.append(row)
    if len(matches) != 1:
        raise mb.MindbodyError("classy_private_prepaid_option_not_eligible")
    return matches[0]


def _state(booking_id: int, status: str, *, error: str = "", service_id: str = "") -> None:
    with core.engine.begin() as conn:
        conn.execute(text(CREATE_TABLE))
        conn.execute(text("""
            INSERT INTO mindbody_prepaid_settlements
                (booking_id, status, service_id, error, attempts, updated_at)
            VALUES (:booking_id, :status, :service_id, :error, 0, CURRENT_TIMESTAMP)
            ON CONFLICT (booking_id) DO UPDATE SET
                status=excluded.status,
                service_id=CASE WHEN excluded.service_id <> ''
                    THEN excluded.service_id
                    ELSE mindbody_prepaid_settlements.service_id END,
                error=excluded.error,
                updated_at=CURRENT_TIMESTAMP
        """), {
            "booking_id": booking_id, "status": status,
            "error": error[:500], "service_id": service_id,
        })


def _snapshot(booking_id: int) -> dict | None:
    with core.SessionLocal() as db:
        booking = db.get(core.Booking, booking_id)
        if (
            not booking or booking.source != "website"
            or booking.status != "reserved"
            or booking.payment_status != "paid"
            or booking.payment_method not in PREPAID_METHODS
        ):
            return None
        klass = booking.klass
        result = {
            "id": booking.id,
            "class_id": str(klass.mindbody_class_id or ""),
            "client_id": str(booking.mindbody_client_id or ""),
            "visit_id": str(booking.mindbody_visit_id or ""),
            "studio_id": klass.studio_id,
            "title": klass.title,
            "method": booking.payment_method,
        }
        return result


def _get_exact_visit(client: mb.WriteClient, snapshot: dict) -> dict | None:
    visits = mb._extract_class_visits(client.get_class_visits(snapshot["class_id"]))
    matches = [
        v for v in visits
        if mb._visit_id(v) == snapshot["visit_id"]
        and mb._visit_client_id(v) == snapshot["client_id"]
        and not mb._visit_is_cancelled(v)
    ]
    if len(matches) != 1:
        return None
    return matches[0]


def _claim(booking_id: int) -> str:
    with core.engine.begin() as conn:
        conn.execute(text(CREATE_TABLE))
        row = conn.execute(
            text("SELECT status FROM mindbody_prepaid_settlements WHERE booking_id=:id FOR UPDATE"),
            {"id": booking_id},
        ).first() if core.engine.dialect.name == "postgresql" else conn.execute(
            text("SELECT status FROM mindbody_prepaid_settlements WHERE booking_id=:id"),
            {"id": booking_id},
        ).first()
        if row is not None:
            # A provider POST can have succeeded even if the response was lost.
            # Such records must only be verified read-only, never re-posted.
            if row[0] in {"posting", "manual_review", "verified", "checking"}:
                return str(row[0])
        conn.execute(text("""
            INSERT INTO mindbody_prepaid_settlements
                (booking_id, status, error, attempts, updated_at)
            VALUES (:id, 'checking', '', 1, CURRENT_TIMESTAMP)
            ON CONFLICT (booking_id) DO UPDATE SET
                status='checking',
                error='',
                attempts=mindbody_prepaid_settlements.attempts+1,
                updated_at=CURRENT_TIMESTAMP
        """), {"id": booking_id})
        return "claimed"


def settle_prepaid_visit(booking_id: int) -> dict:
    """Reconcile one credit-funded visit; safe to call after asynchronous seat hold.

    Does not perform financial writes when disabled/misconfigured. Requires a
    separate eligible 0 EUR prepaid service that the business explicitly owns.
    """
    if not enabled():
        return {"booking_id": booking_id, "status": "setup_required"}
    snapshot = _snapshot(booking_id)
    if snapshot is None:
        return {"booking_id": booking_id, "status": "not_eligible"}
    if not (
        snapshot["class_id"].isdigit()
        and snapshot["visit_id"].isdigit()
        and snapshot["client_id"]
    ):
        return {"booking_id": booking_id, "status": "provider_identity_missing"}

    claim = _claim(booking_id)
    if claim != "claimed":
        return {"booking_id": booking_id, "status": claim}

    service_id = os.getenv("MINDBODY_CLASSY_PREPAID_SERVICE_ID", "").strip()
    provider_post_started = False
    try:
        client = mb.WriteClient.from_env(timeout=18.0)
        current = _get_exact_visit(client, snapshot)
        if current is None:
            _state(booking_id, "blocked", error="original_visit_missing_or_ambiguous")
            return {"booking_id": booking_id, "status": "blocked"}
        current_name, current_service_id = mb._visit_service_identity(current)
        if current_service_id == service_id:
            _state(booking_id, "verified", service_id=service_id)
            return {"booking_id": booking_id, "status": "verified"}
        if (current_service_id or current_name) and not (
            current_name.casefold().startswith(("unpaid", "unverrechn"))
        ):
            _state(booking_id, "manual_review", error="another_service_already_attached")
            return {"booking_id": booking_id, "status": "manual_review"}

        # Require this service to be explicitly eligible for THIS class and
        # NOT publicly sold free. No fallback to Classpass / Wellpass / 1 Class.
        location = mb._resolve_location(client, snapshot["studio_id"], snapshot["title"])
        location_id = str(mb._value(
            location, "Id", "ID", "LocationId", default=""
        ) or "")
        if not location_id.isdigit():
            _state(booking_id, "blocked", error="missing_mindbody_location")
            return {"booking_id": booking_id, "status": "blocked"}
        catalog = client.get_sale_services_for_class(
            snapshot["class_id"], location_id, sell_online=False
        )
        eligible_prepaid_service(catalog, service_id)

        # Test=true is a provider-side validation without a sale/booking change.
        client.checkout_prepaid_class_service(
            client_id=snapshot["client_id"], visit_id=snapshot["visit_id"],
            location_id=location_id, service_id=service_id, test=True,
        )
        if _snapshot(booking_id) != snapshot:
            _state(booking_id, "blocked", error="booking_changed_before_checkout")
            return {"booking_id": booking_id, "status": "blocked"}

        # Durable write-ahead marker. After this point a retry MUST read the
        # provider, not POST another sale, even if our HTTP response is lost.
        _state(booking_id, "posting", service_id=service_id)
        provider_post_started = True
        client.checkout_prepaid_class_service(
            client_id=snapshot["client_id"], visit_id=snapshot["visit_id"],
            location_id=location_id, service_id=service_id, test=False,
        )
        after = _get_exact_visit(client, snapshot)
        if after is not None and mb._visit_service_identity(after)[1] == service_id:
            _state(booking_id, "verified", service_id=service_id)
            return {"booking_id": booking_id, "status": "verified"}
        _state(booking_id, "manual_review", error="provider_checkout_not_verified")
        return {"booking_id": booking_id, "status": "manual_review"}
    except Exception as exc:
        _state(
            booking_id,
            "manual_review" if provider_post_started else "blocked",
            error=("provider_outcome_unknown:" if provider_post_started else "provider_preflight_failed:")
                + type(exc).__name__,
            service_id=service_id if provider_post_started else "",
        )
        return {
            "booking_id": booking_id,
            "status": "manual_review" if provider_post_started else "blocked",
        }


def confirm_existing_prepaid_visit(booking_id: int) -> dict:
    """Read-only provider recovery for a previous uncertain checkout result."""
    snapshot = _snapshot(booking_id)
    service_id = os.getenv("MINDBODY_CLASSY_PREPAID_SERVICE_ID", "").strip()
    if not snapshot or not service_id.isdigit():
        return {"booking_id": booking_id, "status": "setup_required"}
    if not snapshot["class_id"].isdigit() or not snapshot["visit_id"].isdigit():
        return {"booking_id": booking_id, "status": "provider_identity_missing"}
    client = mb.WriteClient.from_env(timeout=18.0)
    visit = _get_exact_visit(client, snapshot)
    if visit is not None and mb._visit_service_identity(visit)[1] == service_id:
        _state(booking_id, "verified", service_id=service_id)
        return {"booking_id": booking_id, "status": "verified"}
    return {"booking_id": booking_id, "status": "manual_review"}


def run_backfill_once() -> dict:
    """At most one future paid visit per run; globally capped by local SQL."""
    if not enabled():
        return {"status": "setup_required"}
    with core.engine.begin() as conn:
        conn.execute(text(CREATE_TABLE))
        used = int(conn.execute(text("""
            SELECT COUNT(*) FROM mindbody_prepaid_settlements
            WHERE status IN ('checking','posting','verified','manual_review','blocked')
              AND updated_at >= :today AND attempts > 0
        """), {"today": datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )}).scalar() or 0)
        if used >= DAILY_LIMIT:
            return {"status": "daily_budget_exhausted"}
        booking_id = conn.execute(text("""
            SELECT b.id FROM bookings b
            JOIN classes c ON c.id=b.class_id
            LEFT JOIN mindbody_prepaid_settlements s ON s.booking_id=b.id
            WHERE s.booking_id IS NULL
              AND b.source='website' AND b.status='reserved'
              AND b.payment_status='paid'
              AND b.payment_method IN ('class_credit','hour_pass','class_pack50')
              AND b.mindbody_sync_status='synced'
              AND b.mindbody_client_id IS NOT NULL
              AND b.mindbody_visit_id IS NOT NULL
              AND c.mindbody_class_id IS NOT NULL
              AND c.starts_at >= :now
              AND b.created_at < :mature
            ORDER BY c.starts_at, b.id LIMIT 1
        """), {
            "now": datetime.now(timezone.utc),
            "mature": datetime.now(timezone.utc)-timedelta(minutes=10),
        }).scalar()
    if booking_id is None:
        return {"status": "no_eligible_booking"}
    return settle_prepaid_visit(int(booking_id))


def _worker() -> None:
    time.sleep(30)
    while True:
        try:
            run_backfill_once()
        except Exception as exc:
            print("Prepaid Mindbody settlement worker:", type(exc).__name__, flush=True)
        time.sleep(CHECK_INTERVAL_SECONDS)


def start_worker() -> None:
    global _started
    if not enabled():
        return
    with _worker_lock:
        if _started:
            return
        _started = True
        threading.Thread(
            target=_worker, name="mindbody-prepaid-settlement", daemon=True
        ).start()
