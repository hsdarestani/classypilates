"""Static cost and integrity contract for selective Mindbody payment recovery."""
from pathlib import Path
import ast

here = Path(__file__).parent
worker = (here / "mindbody_paid_recovery.py").read_text(encoding="utf-8")
sync = (here / "mindbody_sync.py").read_text(encoding="utf-8")
runtime = (here / "runtime_app.py").read_text(encoding="utf-8")
docker = (here / "Dockerfile").read_text(encoding="utf-8")
for name, body in (("worker", worker), ("sync", sync), ("runtime", runtime)):
    ast.parse(body, filename=name)

# The idle worker MUST NOT call expensive full-tenant APIs.
assert "sync_from_mindbody(" not in worker
assert "sync_schedule_availability_fast(" not in worker
assert "sync_client_directory(" not in worker
assert "retry_pending(" not in worker
assert "reconcile_paid_booking_sale(order_id)" in worker
assert "MAX_ATTEMPTS_PER_DAY = 2" in worker
assert "MAX_ATTEMPTS_PER_ORDER = 2" in worker
assert "POLL_HOURS = 6" in worker
assert "MIN_RETRY_HOURS = 6" in worker
for paid_constraint in (
    "po.status='paid'", "po.provider='sumup'",
    "po.provider_payment_id IS NOT NULL",
    "b.payment_method='sumup'", "b.payment_status='paid'",
    "b.status='reserved'", "c.mindbody_class_id IS NOT NULL",
    "b.mindbody_sync_status='synced'",
):
    assert paid_constraint in worker, paid_constraint
assert "SELECT pg_try_advisory_xact_lock(" in worker
assert "ON CONFLICT(order_id) DO UPDATE" in worker
assert 'if not active_visits:' in sync
assert '"no_active_provider_reservation"' in sync
assert '"duplicate_visit_cleanup_incomplete"' in sync
assert '"status": "incomplete" if len(removed_ids) != len(unpaid)' in sync
assert "app.add_event_handler(\"startup\", _start_paid_sale_recovery)" in runtime
assert "COPY mindbody_paid_recovery.py ." in docker
assert "BACKGROUND_SYNC_ENABLED = os.getenv(\"MINDBODY_BACKGROUND_SYNC_ENABLED\", \"false\")" in sync
print("Bounded Mindbody paid recovery contract OK")
