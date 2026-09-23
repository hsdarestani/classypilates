from pathlib import Path

sync = Path("server/mindbody_sync.py").read_text(encoding="utf-8")
runtime = Path("server/runtime_app.py").read_text(encoding="utf-8")
audit = Path("server/mindbody_audit.py").read_text(encoding="utf-8")

required_sync = [
    '"request.hideCanceledClasses": True if public_only else False',
    'return self._public_get("class/classes", params)',
    'def _hide_nonpublic_mindbody_classes(',
    'row.status = "hidden"',
    'def sync_cancelled_classes_window(',
    'public_only=True,',
]
for needle in required_sync:
    assert needle in sync, f"Missing Mindbody public-feed invariant: {needle}"

for fn in ("sync_schedule_availability_fast", "sync_staff_and_assignments", "sync_rosters_window"):
    start = sync.index(f"def {fn}")
    next_def = sync.find("\ndef ", start + 5)
    section = sync[start: next_def if next_def != -1 else len(sync)]
    assert "public_only=True" in section, f"{fn} must use Mindbody public feed"

fast_start = sync.index("def sync_schedule_availability_fast")
fast_end = sync.find("\ndef ", fast_start + 5)
fast_section = sync[fast_start: fast_end if fast_end != -1 else len(sync)]
assert "_hide_nonpublic_mindbody_classes(" in fast_section

staff_start = sync.index("def sync_staff_and_assignments")
staff_end = sync.find("\ndef ", staff_start + 5)
staff_section = sync[staff_start: staff_end if staff_end != -1 else len(sync)]
assert "_hide_nonpublic_mindbody_classes(" in staff_section

runtime_start = runtime.index("def _reconcile_mindbody_availability")
runtime_end = runtime.find("\ndef ", runtime_start + 5)
runtime_section = runtime[runtime_start: runtime_end if runtime_end != -1 else len(runtime)]
assert "public_only=True" in runtime_section
assert "sync_cancelled_classes_window(days=45)" in runtime

assert "public_only=True" in audit
assert '"active_local_not_public"' in audit
assert '"public_status_mismatch"' in audit

roster_start = sync.index("def _reconcile_class_roster")
roster_end = sync.find("\ndef ", roster_start + 5)
roster_section = sync[roster_start: roster_end if roster_end != -1 else len(sync)]
assert 'klass.imported_bookings = 0' in roster_section
assert '_sync_class_availability(' in roster_section
assert '_find_remote_class(client, klass)' in roster_section
assert 'target_reserved - int(local_reserved_after)' not in roster_section
assert 'timedelta(minutes=5)' in roster_section
assert 'booking.mindbody_synced_at = now\n                continue' not in roster_section

# Worker/deadlock invariants: recurring capacity sync must stay lightweight, DDL
# initialization must be process-cached and bounded, and webhook lock waits must
# be retryable rather than pinning an event in "processing" forever.
assert "_sync_state_ready = False" in sync
ensure_start = sync.index("def _ensure_sync_state")
ensure_end = sync.index("\ndef _state_row", ensure_start)
ensure_section = sync[ensure_start:ensure_end]
assert "if _sync_state_ready:" in ensure_section
assert "SET LOCAL lock_timeout = '5s'" in ensure_section

loop_start = sync.index("def _loop()")
loop_end = sync.index("\n\n@core.app.on_event", loop_start)
loop_section = sync[loop_start:loop_end]
assert "sync_schedule_availability_fast()" in loop_section
assert "sync_staff_and_assignments()" not in loop_section
assert "RECONCILE_LOCK.acquire(timeout=20)" in loop_section

webhooks = Path("server/mindbody_webhooks.py").read_text(encoding="utf-8")
process_start = webhooks.index("def _process_batch")
process_end = webhooks.index("\ndef _cleanup_old_events", process_start)
process_section = webhooks[process_start:process_end]
assert "RECONCILE_LOCK.acquire(timeout=15)" in process_section
assert "Mindbody reconciliation busy; webhook will retry" in process_section
assert "sync_schedule_availability_fast()" in process_section

print("Mindbody public feed regression guard: OK")
