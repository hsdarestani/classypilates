"""Dependency-free regression test for Mindbody booking status webhook routing.

A payment/attendance status change must invalidate the affected class roster.
No live provider calls are performed by this test.
"""
import ast
from pathlib import Path

source_path = Path(__file__).with_name("mindbody_webhooks.py")
source = source_path.read_text(encoding="utf-8")
tree = ast.parse(source, filename=str(source_path))
helper = next(
    node for node in tree.body
    if isinstance(node, ast.FunctionDef)
    and node.name == "_needs_roster_reconciliation"
)
module = ast.fix_missing_locations(ast.Module(body=[helper], type_ignores=[]))
scope = {}
exec(compile(module, str(source_path), "exec"), scope)
needs = scope["_needs_roster_reconciliation"]

assert needs({"classRosterBooking.created"})
assert needs({"classRosterBooking.cancelled"})
assert needs({"classRosterBookingStatus.updated"})
assert needs({"classRosterBookingStatus.updated", "class.updated"})
assert not needs({"class.updated"})
assert not needs({"classWaitlistRequest.created"})
assert not needs(set())
assert '"classRosterBookingStatus.updated",' in source
assert "reconcile_roster = _needs_roster_reconciliation(event_ids)" in source
print("Mindbody roster status webhook routing guard OK")
