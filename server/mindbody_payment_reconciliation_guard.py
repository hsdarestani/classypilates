"""Regression guard for the website SumUp -> Mindbody paid-visit bridge.

Runs without network access. It protects the two safety properties that matter most:
1. only a one-class pricing option can be selected (never a pack / Wellhub), and
2. the provider write is a class-linked CheckoutShoppingCart using the site's
   externally-collected "Other" payment mapping (Custom ID 9).
"""
from __future__ import annotations

import mindbody_sync as mb


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

picked = mb._pick_single_class_service(catalog, amount_cents=2800)
assert picked["Id"] == "100071", picked

try:
    mb._pick_single_class_service(
        [service("x", "10 Classes", 219.0, 10, "Series")],
        amount_cents=21900,
    )
except mb.MindbodyError:
    pass
else:
    raise AssertionError("A multi-class pack must never be used to reconcile one visit.")

captured: dict = {}
client = object.__new__(mb.WriteClient)


def fake_write(path: str, payload: dict, *, authenticated: bool = True):
    captured["path"] = path
    captured["payload"] = payload
    captured["authenticated"] = authenticated
    return {"ShoppingCart": {"Id": "test-cart"}}


client._write = fake_write  # type: ignore[method-assign]
result = client.checkout_external_class_payment(
    client_id="100019131",
    class_id="20866",
    location_id="1",
    service_id="100071",
    amount_cents=2800,
)
assert result["ShoppingCart"]["Id"] == "test-cart"
assert captured["path"] == "sale/checkoutshoppingcart"

payload = captured["payload"]
assert payload["Test"] is False
assert payload["InStore"] is True
assert payload["SendEmail"] is False
assert payload["ClientId"] == 100019131
assert payload["LocationId"] == 1
assert payload["Items"] == [
    {
        "Item": {"Type": "Service", "Metadata": {"Id": "100071"}},
        "Quantity": 1,
        "ClassIds": [20866],
    }
]
assert payload["Payments"] == [
    {
        "Type": "Custom",
        "Metadata": {"Amount": 28.0, "Id": 9},
    }
]

query: dict = {}


def fake_get(path: str, params: dict):
    query["path"] = path
    query["params"] = params
    return {"Services": catalog}


client._authorized_get = fake_get  # type: ignore[method-assign]
rows = client.get_sale_services_for_class("20866", "1")
assert len(rows) == len(catalog)
assert query["path"] == "sale/services"
assert query["params"]["request.classId"] == 20866
assert query["params"]["request.locationId"] == 1
assert query["params"]["request.sellOnline"] is True
assert query["params"]["request.includeDiscontinued"] is False

print("Mindbody payment reconciliation guard OK")
