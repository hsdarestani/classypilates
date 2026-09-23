from datetime import datetime, timedelta, timezone
import types

import mindbody_sync as mb
import main as core


# The public schedule request must never use the staff-authenticated getter.
client = mb.WriteClient.__new__(mb.WriteClient)
calls = []

def public_get(self, path, params):
    calls.append(("public", path, dict(params)))
    return {"Classes": []}

def auth_get(self, path, params):
    calls.append(("auth", path, dict(params)))
    return {"Classes": []}

client._public_get = types.MethodType(public_get, client)
client._authorized_get = types.MethodType(auth_get, client)

client.get_classes(
    start_date_time="2026-09-23T00:00:00Z",
    end_date_time="2026-09-24T00:00:00Z",
    public_only=True,
)
assert calls[-1][0] == "public", calls[-1]
assert calls[-1][2]["request.hideCanceledClasses"] is True, calls[-1]

client.get_classes(
    start_date_time="2026-09-23T00:00:00Z",
    end_date_time="2026-09-24T00:00:00Z",
    public_only=False,
)
assert calls[-1][0] == "auth", calls[-1]
assert calls[-1][2]["request.hideCanceledClasses"] is False, calls[-1]


# A provider-backed class absent from the public-visible feed must not stay active.
now = datetime.now(timezone.utc)
with core.SessionLocal() as db:
    active = core.ClassSession(
        studio_id="mid",
        title="Guard hidden class",
        class_type="Reformer",
        starts_at=now + timedelta(days=1),
        duration=50,
        capacity=10,
        imported_bookings=0,
        source_bookings_total=0,
        mindbody_class_id="guard-hidden-remote",
        status="active",
    )
    visible = core.ClassSession(
        studio_id="mid",
        title="Guard public class",
        class_type="Reformer",
        starts_at=now + timedelta(days=1, minutes=30),
        duration=50,
        capacity=10,
        imported_bookings=0,
        source_bookings_total=0,
        mindbody_class_id="guard-public-remote",
        status="active",
    )
    db.add_all([active, visible])
    db.commit()

    hidden_count = mb._hide_nonpublic_mindbody_classes(
        db,
        public_ids={"guard-public-remote"},
        start=now,
        end=now + timedelta(days=2),
        now=now,
    )
    db.commit()
    db.refresh(active)
    db.refresh(visible)
    assert hidden_count >= 1, hidden_count
    assert active.status == "hidden", active.status
    assert visible.status == "active", visible.status

    db.delete(active)
    db.delete(visible)
    db.commit()

print("Mindbody public feed regression guard: OK")
