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

print("Mindbody public feed regression guard: OK")
