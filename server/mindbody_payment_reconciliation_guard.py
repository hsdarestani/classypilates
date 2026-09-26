"""Dependency-free regression guard for SumUp -> Mindbody reconciliation.

CI intentionally runs this before installing the production Python dependencies.
The guard therefore parses the real implementation, executes only its pure pricing
selector, and statically verifies the provider payload invariants.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


SOURCE_PATH = Path(__file__).with_name("mindbody_sync.py")
SOURCE = SOURCE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


class MindbodyError(Exception):
    pass


def module_function(name: str) -> ast.FunctionDef:
    for node in TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"Missing function: {name}")


# Execute only the pure service-selection helpers from the production source.
namespace: dict[str, Any] = {"Any": Any, "MindbodyError": MindbodyError}
nodes = [
    module_function("_value"),
    module_function("_service_price_cents"),
    module_function("_pick_single_class_service"),
]
ast.fix_missing_locations(module := ast.Module(body=nodes, type_ignores=[]))
exec(compile(module, str(SOURCE_PATH), "exec"), namespace)

pick = namespace["_pick_single_class_service"]


def service(service_id: str, name: str, price: float, count: int, service_type: str = "DropIn"):
    return {
        "Id": service_id,
        "Name": name,
        "Price": price,
        "OnlinePrice": price,
        "Count": count,
        "Type": service_type,
        "ProgramId": 23,
        "SellOnline": True,
    }


catalog = [
    service("100006", "1 Class ", 28.0, 1),
    service("100071", "1 Class", 28.0, 1),
    service("100007", "10 Classes", 219.0, 10, "Series"),
    service("100061", "Wellhub", 0.0, 1),
]
picked = pick(catalog, amount_cents=2800)
assert picked["Id"] == "100071", picked

try:
    pick([service("x", "10 Classes", 219.0, 10, "Series")], amount_cents=21900)
except MindbodyError:
    pass
else:
    raise AssertionError("A multi-class pack must never reconcile one class visit.")


# Inspect the actual WriteClient methods rather than duplicating their payload logic.
write_client = next(
    node for node in TREE.body
    if isinstance(node, ast.ClassDef) and node.name == "WriteClient"
)
methods = {
    node.name: node
    for node in write_client.body
    if isinstance(node, ast.FunctionDef)
}
checkout = ast.get_source_segment(SOURCE, methods["checkout_external_class_payment"]) or ""
services = ast.get_source_segment(SOURCE, methods["get_sale_services_for_class"]) or ""

required_checkout_fragments = [
    '"sale/checkoutshoppingcart"',
    '"Type": "Service"',
    '"ClassIds": [int(class_id)]',
    '"Type": "Custom"',
    '"Amount": amount',
    '"Id": MINDBODY_EXTERNAL_PAYMENT_METHOD_ID',
    '"Test": False',
    '"InStore": True',
    '"SendEmail": False',
]
for fragment in required_checkout_fragments:
    assert fragment in checkout, f"Missing checkout safety invariant: {fragment}"

required_service_fragments = [
    '"sale/services"',
    '"request.classId": int(class_id)',
    '"request.locationId": int(location_id)',
    '"request.sellOnline": True',
    '"request.includeDiscontinued": False',
]
for fragment in required_service_fragments:
    assert fragment in services, f"Missing service-query invariant: {fragment}"

assert 'MINDBODY_EXTERNAL_PAYMENT_METHOD_ID = int(os.getenv("MINDBODY_EXTERNAL_PAYMENT_METHOD_ID", "9") or "9")' in SOURCE
assert 'booking.payment_method != "sumup"' in SOURCE
assert 'booking.payment_status != "paid"' in SOURCE
assert 'booking.source != "website"' in SOURCE
assert 'order.mindbody_sale_status == "synced"' in SOURCE

# The runtime composes two retry wrappers. They must capture different base
# functions; reusing one global capture name previously made the mirror recurse
# forever and prevented expired SumUp holds from being released.
runtime_source = Path(__file__).with_name("runtime_app.py").read_text(encoding="utf-8")
assert "_base_retry_pending = mindbody_sync.retry_pending" in runtime_source
assert "retried = _base_retry_pending()" in runtime_source
assert "_retry_pending_before_hold_cleanup = mindbody_sync.retry_pending" in runtime_source
assert "retried = _retry_pending_before_hold_cleanup()" in runtime_source
assert "_original_retry_pending" not in runtime_source

print("Mindbody payment reconciliation guard OK")
