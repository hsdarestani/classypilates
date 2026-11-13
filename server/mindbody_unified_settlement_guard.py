"""Pure and static regression tests for prepaid/sumup Mindbody accounting safety.

This is a dependency-free CI guard: no credential, API or database access.
"""
from pathlib import Path
from types import SimpleNamespace
import ast

here = Path(__file__).parent
source = (here / "mindbody_prepaid_settlement.py").read_text(encoding="utf-8")
sync = (here / "mindbody_sync.py").read_text(encoding="utf-8")
feedback = (here / "feedback_app.py").read_text(encoding="utf-8")
runtime = (here / "runtime_app.py").read_text(encoding="utf-8")
docker_compose = (here.parent / "docker-compose.yml").read_text(encoding="utf-8")
for name, body in (("prepaid", source), ("sync", sync), ("runtime", runtime)):
    ast.parse(body, filename=name)

def fn(module_source, name):
    return next(
        n for n in ast.parse(module_source).body
        if isinstance(n, ast.FunctionDef) and n.name == name
    )

class ProviderError(Exception):
    pass

def val(row, *keys, default=None):
    for k in keys:
        if row.get(k) is not None:
            return row[k]
    return default

def cents(row):
    return int(round(float(row.get("OnlinePrice", row.get("Price", 0))) * 100))

namespace = {
    "mb": SimpleNamespace(
        _value=val, _service_price_cents=cents, MindbodyError=ProviderError,
    ),
    "PRIVATE_SERVICE_NAMES": {"classy prepaid", "classy website prepaid"},
}
body = ast.fix_missing_locations(ast.Module(
    body=[fn(source, "eligible_prepaid_service")], type_ignores=[]
))
exec(compile(body, "prepaid_selector", "exec"), namespace)
pick = namespace["eligible_prepaid_service"]
option = {
    "Id": "770111", "Name": "Classy Website Prepaid",
    "Price": 0, "OnlinePrice": 0, "Count": 1, "Type": "DropIn",
}
assert pick([option], "770111") == option
for invalid in (
    dict(option, Name="Classpass"),
    dict(option, Name="Wellpass"),
    dict(option, Name="1 Class"),
    dict(option, Price=28, OnlinePrice=28),
    dict(option, Count=10),
    dict(option, Type="Series"),
    dict(option, Id="999999"),
):
    try:
        pick([invalid], "770111")
    except ProviderError:
        pass
    else:
        raise AssertionError(f"Unauthorized prepaid service selected: {invalid!r}")
try:
    pick([option, option], "770111")
except ProviderError:
    pass
else:
    raise AssertionError("Ambiguous prepaid option selected")

# Provider zero-money checkout: exact prior visit, not ClassId/new booking.
method = next(
    n for n in ast.parse(sync).body
    if isinstance(n, ast.ClassDef) and n.name == "WriteClient"
)
checkout = ast.get_source_segment(
    sync, next(n for n in method.body
               if isinstance(n, ast.FunctionDef)
               and n.name == "checkout_prepaid_class_service")
)
assert '"VisitIds": [int(visit_id)]' in checkout
assert '"Payments": []' in checkout
assert '"Test": bool(test)' in checkout
assert '"ClassIds"' not in checkout
assert '"Amount": 28' not in checkout
assert 'prepaid_checkout_invalid_provider_identity' in checkout

# Disabled-by-default provider writes, exact VisitId verification, durable
# write-ahead marker, preflight first, unknown-outcome quarantine.
assert 'MINDBODY_CLASSY_PREPAID_SETTLEMENT_ENABLED", "false"' in source
assert 'MINDBODY_CLASSY_PREPAID_SERVICE_ID' in source
assert 'PREPAID_METHODS = {"class_credit", "hour_pass", "class_pack50"}' in source
assert 'client.get_sale_services_for_class(' in source
assert 'sell_online=False' in source
assert 'and mb._visit_client_id(v) == snapshot["client_id"]' in source
assert 'and mb._visit_id(v) == snapshot["visit_id"]' in source
assert 'test=True' in source and 'test=False' in source
assert source.index('test=True') < source.index('_state(booking_id, "posting"') < source.index('test=False')
assert '"manual_review" if provider_post_started else "blocked"' in source
assert 'if row[0] in {"posting", "manual_review", "verified", "checking"}' in source
assert '"status": "setup_required"' in source
assert 'DAILY_LIMIT = 8' in source
assert 'LEFT JOIN mindbody_prepaid_settlements s' in source
assert 's.booking_id IS NULL' in source
assert "app.add_event_handler(\"startup\", _prepaid_settlement.start_worker)" in runtime
assert 'core.require("bookings.manage")' in runtime
assert 'core.can(user, "finance.view")' in runtime
assert 'if enabled():' in feedback
assert 'settle_prepaid_visit(booking_id)' in feedback
assert 'MINDBODY_CLASSY_PREPAID_SERVICE_ID' in docker_compose
assert 'MINDBODY_CLASSY_PREPAID_SETTLEMENT_ENABLED' in docker_compose

# SumUp uncertain POST outcomes must NEVER auto-retry creating a sale.
assert 'provider_write_attempted = True' in sync
assert '"manual_review" if provider_write_attempted else "failed"' in sync
assert '"Test": False' in sync  # existing standard paid SumUp checkout still enabled
print("Classy prepaid & SumUp safe financial settlement guard OK")
