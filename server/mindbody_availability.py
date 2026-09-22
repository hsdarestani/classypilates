from __future__ import annotations

from typing import Any


def _as_nonnegative_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return max(0, int(value))
    except Exception:
        return None


def _provider_unavailable(value: Any) -> bool:
    if value is False:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"false", "0", "no", "off"}
    if isinstance(value, (int, float)):
        return value == 0
    return False


def compute_public_availability(
    *,
    effective_capacity: int,
    local_reserved: int,
    cached_imported: int,
    total_booked: Any,
    web_capacity: Any,
    web_booked: Any,
    is_available: Any,
) -> tuple[int, int, int, int | None]:
    """Return (available, target_reserved, imported, normalized_total_booked).

    Mindbody public bookability is authoritative. Physical free space alone is not
    enough: a class can be unavailable because its public booking window is closed,
    or because WebCapacity is exhausted/zero.
    """
    capacity = max(0, int(effective_capacity or 0))
    local = max(0, int(local_reserved or 0))
    cached = max(0, int(cached_imported or 0))

    total = _as_nonnegative_int(total_booked)
    web_cap = _as_nonnegative_int(web_capacity)
    web_used = _as_nonnegative_int(web_booked)

    if _provider_unavailable(is_available):
        available = 0
    else:
        physical_available = None
        if total is not None:
            physical_available = max(0, capacity - total)

        web_available = None
        if web_cap is not None:
            # WebCapacity=0 is a real zero-bookable state even if Mindbody omits
            # TotalWebBooked. Treat a missing web-booked counter as zero usage,
            # not as a reason to ignore the web cap entirely.
            web_available = max(0, web_cap - (web_used or 0))

        if physical_available is not None and web_available is not None:
            available = min(physical_available, web_available)
        elif physical_available is not None:
            available = physical_available
        elif web_available is not None:
            available = min(max(0, capacity - local), web_available)
        else:
            # Mindbody can hide capacity counters. Preserve the last provider-backed
            # occupancy instead of reopening a class from local rows alone.
            available = max(0, capacity - local - cached)

    available = min(capacity, max(0, int(available)))
    target_reserved = max(0, capacity - available)
    imported = max(0, target_reserved - local)
    return available, target_reserved, imported, total
