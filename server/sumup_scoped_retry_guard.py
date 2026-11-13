"""No-network contract for selected, provider-verified SumUp payment recovery."""
import ast
from pathlib import Path

root = Path(__file__).parent
runtime = (root / "runtime_app.py").read_text(encoding="utf-8")
main = (root / "main.py").read_text(encoding="utf-8")
staff = (root.parent / "public" / "staff.js").read_text(encoding="utf-8")
ast.parse(runtime, filename="runtime_app.py")
ast.parse(main, filename="main.py")
tree = ast.parse(runtime)
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
          and n.name == "retry_verified_sumup_pricing_blocker")
source = ast.get_source_segment(runtime, fn)

for value in (
    'core.require("bookings.manage")',
    'core.can(user, "finance.view")',
    'order.mindbody_sale_status != "manual_review"',
    'order.mindbody_sale_error != "pricing_option_not_enabled_for_class"',
    'order.provider != "sumup"',
    'order.status != "paid"',
    'booking.payment_method != "sumup"',
    'booking.payment_status != "paid"',
    'feedback._sumup_request(',
    'feedback._sumup_amount_cents(provider) == amount_cents',
    'os.getenv("SUMUPMERCHANT", "")',
    'order.mindbody_sale_status = "pending"',
    'mindbody_sync.reconcile_paid_booking_sale(order_id)',
):
    assert value in source, value

assert source.index('feedback._sumup_request(') < source.index('order.mindbody_sale_status = "pending"')
assert 'profile.credits' not in source
assert 'booking.payment_status = "paid"' not in source
assert '"order_id": order.id' in main
assert "data-retry-sumup" in staff
assert "document.querySelectorAll('[data-verify-prepaid]')" in staff
print("Scoped SumUp provider-verified retry contract OK")
