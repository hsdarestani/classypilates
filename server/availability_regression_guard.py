from types import SimpleNamespace

from mindbody_sync import _sync_class_availability


def make_class(capacity=10, imported=0, source=0):
    return SimpleNamespace(
        capacity=capacity,
        imported_bookings=imported,
        source_bookings_total=source,
    )


def spots(klass, local_reserved):
    return max(
        0,
        int(klass.capacity or 0)
        - int(klass.imported_bookings or 0)
        - int(local_reserved),
    )


# Mindbody explicitly says the class is not available for public booking.
klass = make_class(capacity=10, imported=2, source=2)
_sync_class_availability(
    None,
    klass,
    {
        "MaxCapacity": 10,
        "TotalBooked": 2,
        "WebCapacity": 10,
        "TotalWebBooked": 2,
        "IsAvailable": False,
    },
    0,
)
assert spots(klass, 0) == 0, (klass.capacity, klass.imported_bookings)

# A zero web capacity means zero public spots even if WebBooked is omitted.
klass = make_class(capacity=10, imported=2, source=2)
_sync_class_availability(
    None,
    klass,
    {
        "MaxCapacity": 10,
        "TotalBooked": 2,
        "WebCapacity": 0,
        "TotalWebBooked": None,
        "IsAvailable": True,
    },
    0,
)
assert spots(klass, 0) == 0, (klass.capacity, klass.imported_bookings)

# Normal public capacity remains accurate.
klass = make_class(capacity=10, imported=0, source=0)
_sync_class_availability(
    None,
    klass,
    {
        "MaxCapacity": 10,
        "TotalBooked": 4,
        "WebCapacity": 10,
        "TotalWebBooked": 4,
        "IsAvailable": True,
    },
    0,
)
assert spots(klass, 0) == 6, (klass.capacity, klass.imported_bookings)

# Local Classy holds are subtracted without double-counting provider occupancy.
klass = make_class(capacity=10, imported=0, source=0)
_sync_class_availability(
    None,
    klass,
    {
        "MaxCapacity": 10,
        "TotalBooked": 4,
        "WebCapacity": 10,
        "TotalWebBooked": 4,
        "IsAvailable": True,
    },
    1,
)
assert spots(klass, 1) == 6, (klass.capacity, klass.imported_bookings)

print("Mindbody availability regression guard: OK")
