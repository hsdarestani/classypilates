"""Regression checks for time based 50-hour package, without external credentials."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
backend = (ROOT / "server/feedback_app.py").read_text(encoding="utf-8")
core = (ROOT / "server/main.py").read_text(encoding="utf-8")
shop = (ROOT / "public/shop.js").read_text(encoding="utf-8")
booking = (ROOT / "public/booking-flow.js").read_text(encoding="utf-8")
landing = (ROOT / "public/50-kurse.html").read_text(encoding="utf-8")
route = (ROOT / "public/50-kurse/index.html").read_text(encoding="utf-8")
tree = ast.parse(backend)

def get_function(name):
    return next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)

def source_of(name):
    return ast.get_source_segment(backend, get_function(name)) or ""

catalog = next(node for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "SHOP_PRODUCTS" for t in node.targets))
products = ast.literal_eval(catalog.value)
assert products["hour50"] == {"name": "50 Stunden · 12 Monate", "price": 69900, "credits": 0, "minutes": 3000}
assert 'price:69900' in shop and 'id:\'hour50\'' in shop
assert 'href="/shop?product=class50"' in landing
assert "mailto:" not in landing
assert "50 Kurse" in landing and "699 €" in landing and "12 Monate" in landing
assert "3000 Minuten" not in landing and "50 Stunden" not in landing and "13,98" not in landing
assert products["class50"] == {"name": "50 Kurse · 12 Monate", "price": 69900, "credits": 0, "classes": 50}
assert landing == route, "Short URL directory must display the same offer"
assert "50-kurse" in (ROOT / "public/sitemap.xml").read_text(encoding="utf-8")

models = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
assert {"HourPass", "HourPassUsage"}.issubset(models)
creation = source_of("create_sumup_checkout")
assert "HourPass(order_id=order.id" in creation
assert "hour_pass_one_per_order" in creation
payment = source_of("_sync_sumup_order")
for marker in ("status == \"PAID\"", 'hour_pass.status = "active"', "activated + relativedelta(months=12)", "order.credited = True"):
    assert marker in payment, marker
spend = source_of("reserve_hour_minutes")
for marker in ("with_for_update()", "p.total_minutes - p.used_minutes", "row.used_minutes += qty", "HourPass.expires_at > class_start"):
    assert marker in spend, marker
refund = source_of("refund_hour_minutes")
for marker in ("HourPassUsage.refunded.is_(False)", "p.used_minutes - usage.minutes", "usage.refunded = True"):
    assert marker in refund, marker
book = source_of("public_booking_v2")
for marker in ("reserve_hour_minutes(user.email, int(c.duration), c.starts_at, db)", "HourPassUsage(pass_id=pass_id, booking_id=booking.id, minutes=minutes)", 'payment_method="hour_pass"'):
    assert marker in book, marker
assert "refund_hour_minutes(booking, db)" in source_of("_hold_booking_background")
assert "refund_hour_minutes(booking, db)" in source_of("delete_class_v2")
assert '"hour_pass"' in core and "refund_hour_minutes(booking, db)" in core
assert "active_hour_minutes(user.email, db)" in core
assert "useCredit:wizard.payment==='hour_pass'||wizard.payment==='class_credit'" in booking
class_pack = source_of("reserve_class_pack_credit")
for marker in ("with_for_update()", "p.used_classes", "ClassPack.expires_at > class_start"):
    assert marker.replace("p.used_classes", "row.used_classes") in class_pack, marker
class_refund = source_of("refund_class_pack_credit")
assert "ClassPackUsage.refunded.is_(False)" in class_refund
assert "pack.used_classes - 1" in class_refund and "usage.refunded = True" in class_refund
assert "ClassPack(order_id=order.id" in creation
assert "class_pack.status = \"active\"" in payment
assert '"class_pack50"' in book
assert '"class_pack50"' in core
print("Legacy hour passes and new 50-class packs: checkout, expiry, redemption and refunds OK")
