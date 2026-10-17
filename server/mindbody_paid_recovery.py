"""Bounded recovery of paid SumUp bookings without restarting bulk Mindbody sync.

No provider calls are made on a normal idle tick. Only a locally confirmed PAID
SumUp order whose Mindbody sale is unfinished can enter this queue. Every
attempt is recorded in PostgreSQL before contacting Mindbody; duplicate/sale
idempotency remains in reconcile_paid_booking_sale().
"""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

import mindbody_sync as mb

core = mb.core
_started = False
_guard = threading.Lock()

# This is a hard ceiling on *attempts*, not provider HTTP requests per attempt.
# Never enable the wide three-minute mirror to repair payment failures.
MAX_ATTEMPTS_PER_DAY = 2
MAX_ATTEMPTS_PER_ORDER = 2
MIN_RETRY_HOURS = 6
MIN_AGE_MINUTES = 10
POLL_HOURS = 6

CREATE_REPAIR_TABLE = """
CREATE TABLE IF NOT EXISTS mindbody_paid_sale_recovery (
    order_id INTEGER PRIMARY KEY,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMP WITH TIME ZONE
)
"""


def _ready() -> bool:
    return (
        os.getenv("MINDBODY_PAYMENT_RECOVERY_ENABLED", "true").lower()
        in {"true", "1", "yes", "on"}
        and mb.SYNC_ENABLED
        and mb.capability_status()["configured"]
    )


def _claim_one() -> int | None:
    now = datetime.now(timezone.utc)
    with core.engine.begin() as conn:
        if core.engine.dialect.name == "postgresql":
            # Safe if two API instances happen to overlap during a deployment.
            conn.execute(text("SET LOCAL lock_timeout = '2s'"))
            if not conn.execute(text("SELECT pg_try_advisory_xact_lock(72819420)")).scalar():
                return None
        conn.execute(text(CREATE_REPAIR_TABLE))
        used = int(conn.execute(
            text("SELECT COUNT(*) FROM mindbody_paid_sale_recovery WHERE last_attempt_at >= :today"),
            {"today": now.replace(hour=0, minute=0, second=0, microsecond=0)},
        ).scalar() or 0)
        if used >= MAX_ATTEMPTS_PER_DAY:
            return None

        # Everything here is local SQL. Nothing is fetched from Mindbody until a
        # confirmed paid order is claimed. A recent payment's in-flight callback
        # has ten minutes to finish without being raced by this worker.
        order_id = conn.execute(text("""
            SELECT po.id
            FROM payment_orders po
            JOIN bookings b ON b.reference = po.booking_reference
            JOIN classes c ON c.id = b.class_id
            LEFT JOIN mindbody_paid_sale_recovery attempts ON attempts.order_id=po.id
            WHERE po.status='paid'
              AND po.provider='sumup'
              AND po.provider_payment_id IS NOT NULL
              AND po.booking_reference IS NOT NULL
              AND po.mindbody_sale_status IN ('', 'pending', 'failed')
              AND po.created_at >= :earliest
              AND po.updated_at < :mature
              AND b.source='website'
              AND b.status='reserved'
              AND b.payment_method='sumup'
              AND b.payment_status='paid'
              AND b.amount_cents > 0
              AND b.mindbody_client_id IS NOT NULL
              AND b.mindbody_sync_status='synced'
              AND c.mindbody_class_id IS NOT NULL
              AND c.starts_at >= :min_class_start
              AND COALESCE(attempts.attempts,0) < :max_per_order
              AND (attempts.last_attempt_at IS NULL OR attempts.last_attempt_at < :cooldown)
            ORDER BY c.starts_at ASC, po.id ASC
            LIMIT 1
        """), {
            "earliest": datetime(2026, 9, 26, tzinfo=timezone.utc),
            "mature": now - timedelta(minutes=MIN_AGE_MINUTES),
            "min_class_start": now - timedelta(days=1),
            "cooldown": now - timedelta(hours=MIN_RETRY_HOURS),
            "max_per_order": MAX_ATTEMPTS_PER_ORDER,
        }).scalar()
        if order_id is None:
            return None
        conn.execute(text("""
            INSERT INTO mindbody_paid_sale_recovery(order_id, attempts, last_attempt_at)
            VALUES (:id, 1, :now)
            ON CONFLICT(order_id) DO UPDATE
            SET attempts=mindbody_paid_sale_recovery.attempts + 1,
                last_attempt_at=excluded.last_attempt_at
        """), {"id": int(order_id), "now": now})
    return int(order_id)


def run_once() -> dict[str, int | str]:
    """Process at most one verified paid sale, bounded across restarts."""
    if not _ready():
        return {"status": "disabled", "attempted": 0}
    try:
        order_id = _claim_one()
    except Exception as exc:
        print("Mindbody payment recovery database check failed:", type(exc).__name__, flush=True)
        return {"status": "database_error", "attempted": 0}
    if order_id is None:
        return {"status": "no_eligible_sale_or_budget_exhausted", "attempted": 0}

    # This function checks the live roster BEFORE posting a sale and is
    # idempotent for duplicate callbacks/HTTP failures.
    succeeded = bool(mb.reconcile_paid_booking_sale(order_id))
    result = {"status": "reconciled" if succeeded else "requires_followup", "attempted": 1}
    print("Mindbody payment recovery:", json.dumps(result, sort_keys=True), flush=True)
    return result


def _worker() -> None:
    time.sleep(30)
    while True:
        try:
            run_once()
        except Exception as exc:
            print("Mindbody payment recovery worker:", type(exc).__name__, flush=True)
        time.sleep(POLL_HOURS * 3600)


def start_worker() -> None:
    global _started
    if not _ready():
        return
    with _guard:
        if _started:
            return
        _started = True
        threading.Thread(target=_worker, name="mindbody-paid-recovery", daemon=True).start()


if __name__ == "__main__":
    # Manual invocation is still budgeted and does not force any bulk API sync.
    print(json.dumps(run_once(), sort_keys=True))
