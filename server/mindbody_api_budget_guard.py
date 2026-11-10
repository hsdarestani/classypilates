"""Dependency-free regression checks for low-call Mindbody integration.

Run: python server/mindbody_api_budget_guard.py
No network, Mindbody credentials, or database required.
"""
from __future__ import annotations

import ast
import os
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SYNC = (ROOT / "mindbody_sync.py").read_text()
HOOKS = (ROOT / "mindbody_webhooks.py").read_text()
RUNTIME = (ROOT / "runtime_app.py").read_text()
COMPOSE = (ROOT.parent / "docker-compose.yml").read_text()

# Static guard against reverting the problematic 3-minute polling defaults.
assert 'MINDBODY_BACKGROUND_SYNC_ENABLED", "false"' in SYNC
assert 'MINDBODY_SYNC_INTERVAL_SECONDS", "28800"' in SYNC
assert 'MINDBODY_SYNC_INTERVAL_SECONDS:-28800' in COMPOSE
assert 'MINDBODY_ROSTER_SYNC_INTERVAL_SECONDS", "86400"' in RUNTIME
assert "sync_recent_completed_rosters(lookback_hours=30)" in RUNTIME
assert 'event_id == "classRosterBookingStatus.updated"' in HOOKS
assert 'mindbody_sync.reconcile_remote_class(' in HOOKS

# Execute only the isolated staff cache definitions, not the production app.
start = SYNC.index("# Cache the slow-changing Mindbody staff directory")
end = SYNC.index("\ndef _canonical_coach_name(", start)
cache_section = SYNC[start:end]
scope: dict[str, Any] = {
    "threading": threading, "os": os, "time": time, "Any": Any,
    "_remote_staff_id": lambda row: str(row.get("Id") or ""),
    "_extract_list": lambda payload, names: next(
        (payload[name] for name in names if isinstance(payload.get(name), list)), []
    ),
}
exec("from __future__ import annotations\n" + cache_section, scope)
assert scope["_STAFF_CACHE_TTL_SECONDS"] >= 60

class FakeMindbody:
    def __init__(self):
        self.calls = 0
        self.rows = [{"Id": 1, "Name": "First teacher"}]

    def get_staff(self, *, limit, offset):
        self.calls += 1
        return {"StaffMembers": self.rows[offset: offset + limit]}

client = FakeMindbody()
load = scope["_load_remote_staff"]
first = load(client, required_remote_ids={"1"})
assert client.calls == 1
first[0]["Name"] = "Mutated local copy"
second = load(client, required_remote_ids={"1"})
assert client.calls == 1 and second[0]["Name"] == "First teacher"

# A new teacher in a class forces a safe directory refresh.
client.rows.append({"Id": 2, "Name": "New teacher"})
assert len(load(client, required_remote_ids={"2"})) == 2
assert client.calls == 2
scope["_invalidate_remote_staff_cache"]()
assert len(load(client, required_remote_ids={"1"})) == 2
assert client.calls == 3

# Observability adds no upstream traffic and never exposes client information.
import mindbody_usage
before = mindbody_usage.snapshot()["total"]
mindbody_usage.record_call("GET", "class/classes")
mindbody_usage.record_call("POST", "usertoken/issue")
after = mindbody_usage.snapshot()
assert after["total"] == before + 2
assert any(row["endpoint"] == "class/classes" for row in after["by_endpoint"])
assert after["scope"] == "this_server_process_only"

ast.parse(SYNC)
ast.parse(HOOKS)
ast.parse(RUNTIME)
print("Mindbody low-call regression checks passed")
