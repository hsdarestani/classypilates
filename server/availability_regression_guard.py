from mindbody_availability import compute_public_availability


def run_case(**kwargs):
    available, target_reserved, imported, total = compute_public_availability(**kwargs)
    return available, target_reserved, imported, total


# Mindbody explicitly says the class is not available for public booking.
available, _, imported, _ = run_case(
    effective_capacity=10,
    local_reserved=0,
    cached_imported=2,
    total_booked=2,
    web_capacity=10,
    web_booked=2,
    is_available=False,
)
assert available == 0 and imported == 10, (available, imported)

# A zero web capacity means zero public spots even if WebBooked is omitted.
available, _, imported, _ = run_case(
    effective_capacity=10,
    local_reserved=0,
    cached_imported=2,
    total_booked=2,
    web_capacity=0,
    web_booked=None,
    is_available=True,
)
assert available == 0 and imported == 10, (available, imported)

# Normal public capacity remains accurate.
available, _, imported, total = run_case(
    effective_capacity=10,
    local_reserved=0,
    cached_imported=0,
    total_booked=4,
    web_capacity=10,
    web_booked=4,
    is_available=True,
)
assert available == 6 and imported == 4 and total == 4, (available, imported, total)

# A local Classy hold is not double-counted against provider occupancy.
available, _, imported, _ = run_case(
    effective_capacity=10,
    local_reserved=1,
    cached_imported=0,
    total_booked=4,
    web_capacity=10,
    web_booked=4,
    is_available=True,
)
assert available == 6 and imported == 3, (available, imported)

# If Mindbody hides all counters, preserve the previous provider-backed occupancy.
available, _, imported, _ = run_case(
    effective_capacity=10,
    local_reserved=1,
    cached_imported=5,
    total_booked=None,
    web_capacity=None,
    web_booked=None,
    is_available=True,
)
assert available == 4 and imported == 5, (available, imported)

print("Mindbody availability regression guard: OK")
