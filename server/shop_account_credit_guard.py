"""Regression assertions for signed-in SumUp credit identity and historical Mindbody alerts.

This check is dependency-free and performs no financial or provider writes.
"""
import ast
from pathlib import Path

root = Path(__file__).parent
feedback = (root / "feedback_app.py").read_text(encoding="utf-8")
main = (root / "main.py").read_text(encoding="utf-8")
shop = (root.parent / "public" / "shop.js").read_text(encoding="utf-8")
for path, source in (("feedback_app.py", feedback), ("main.py", main)):
    ast.parse(source, filename=path)

checkout = feedback.split("def create_sumup_checkout(", 1)[1].split("\n@app.", 1)[0]
assert "Depends(core.optional_user)" in checkout
assert 'core.portal_for(customer) == "/account"' in checkout
assert 'email != customer.email.strip().lower()' in checkout
assert 'HTTPException(409, "checkout_email_must_match_account")' in checkout
assert checkout.index("checkout_email_must_match_account") < checkout.index("_sumup_request(\"/v0.1/checkouts\", method=\"POST\"")
assert '"credited": bool(order.credited)' in feedback
assert '"credits": int(order.credits or 0)' in feedback
assert "state.accountEmail" in shop
assert "await syncSignedInCustomer()" in shop
assert "email:state.accountEmail||" in shop
assert "credited=Boolean(data.credited)" in shop

# A paid order can be credited only after verifying SumUp and can be applied
# at most once, under the existing row lock. The order's checkout email stays
# its immutable purchase identity; no blind cross-account transfers.
sync = feedback.split("def _sync_sumup_order(", 1)[1].split("\n@app.", 1)[0]
assert ".with_for_update()" in sync
assert 'if status == "PAID":' in sync
assert "elif not order.credited:" in sync
assert "profile.credits += order.credits" in sync
assert "order.credited = True" in sync

alert = main.split('mindbody_payment_attention = []', 1)[1].split('@app.get("/api/staff/finance")', 1)[0]
assert 'PaymentOrder.mindbody_sale_status.in_(' in alert
assert '"manual_review"' in alert
assert 'ClassSession.starts_at >= now - timedelta(days=1)' not in alert
assert '.order_by(PaymentOrder.id.desc())' in alert
print("Shop credit identity and Mindbody visibility guard OK")
