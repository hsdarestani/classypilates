"""Dependency-free regression checks for prepaid booking payment integrity.
No network or payment writes: purely checks the source-level contract.
"""
from pathlib import Path
import ast

here = Path(__file__).parent
main = (here / "main.py").read_text(encoding="utf-8")
runtime = (here / "runtime_app.py").read_text(encoding="utf-8")
staff = (here.parent / "public" / "staff.js").read_text(encoding="utf-8")
for name, source in (("main.py", main), ("runtime_app.py", runtime)):
    ast.parse(source, filename=name)

summary = main.split('def prepaid_booking_audit(', 1)[1].split('\n@app.', 1)[0]
assert 'Depends(require("finance.view"))' in summary
assert '"class_credit", "hour_pass", "class_pack50"' in summary
assert 'Booking.payment_status == "paid"' in summary
assert 'Booking.status == "reserved"' in summary
assert '"provider_payment_verified": False' in summary
assert '"provider_payment_status": "not_verified"' in summary
assert 'get_class_visits' not in summary
assert 'profile.credits' not in summary

verify_node = next(
    node for node in ast.parse(runtime).body
    if isinstance(node, ast.FunctionDef) and node.name == "verify_classy_prepaid_visit"
)
verify = ast.get_source_segment(runtime, verify_node) or ""
assert 'core.require("finance.view")' in verify
assert 'mindbody_sync._visit_id(visit) == visit_id' in verify
assert 'mindbody_sync._visit_client_id(visit) == client_id' in verify
assert 'mindbody_sync._visit_is_cancelled(visit)' in verify
assert 'client.get_class_visits(class_id)' in verify
assert 'service_name.casefold().startswith(("unpaid", "unverrechn"))' in verify
assert '"provider_unpaid"' in verify
assert '"provider_service_attached_needs_entitlement_match"' in verify
for forbidden in ('checkout_external_class_payment', 'add_to_class(', 'profile.credits +=',
                  'create_sumup_checkout', 'reconcile_paid_booking_sale', 'sync_from_mindbody(',
                  'db.commit(', 'client._write('):
    assert forbidden not in verify, forbidden

assert 'api(\'/api/staff/mindbody/prepaid-audit?limit=20\')' in staff
assert "data-verify-prepaid" in staff
assert 'Mindbody Zahlung noch nicht verifiziert' in staff
print("Classy prepaid-Mindbody audit and zero-write integrity guard OK")
