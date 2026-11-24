"""Read-only shop orders regression guard (no database or provider access)."""
import ast
from pathlib import Path
root = Path(__file__).parent
source = (root / "main.py").read_text()
tree = ast.parse(source)
funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
read = ast.get_source_segment(source, funcs["_staff_shop_orders"])
route = ast.get_source_segment(source, funcs["staff_shop_orders"])
profile = ast.get_source_segment(source, funcs["staff_customer_profile"])
assert "PaymentOrder.booking_reference.is_(None)" in read
assert "PaymentOrder.credited.is_(False)" in read
assert 'PaymentOrder.status == "paid"' in read
assert "account_exists" in read and "awaiting_account" in read
assert ".offset(offset).limit(limit)" in read
for forbidden in (".commit(", ".flush(", ".add(", ".delete(", "with_for_update", "urlopen", "_sumup_request"):
    assert forbidden not in read, forbidden
assert 'require("finance.view")' in route
assert 'can(user, "finance.view")' in profile
assert "email=customer_email" in profile
html = (root.parent / "public/staff.html").read_text()
js = (root.parent / "public/staff.js").read_text()
assert 'data-view="shoporders" data-perm="finance.view"' in html
assert "api('/api/staff/shop-orders?" in js
assert "payload.shop_orders" in js
assert "missing_credit" in js
print("Shop orders read-only, permission and allocation regression guard OK")
