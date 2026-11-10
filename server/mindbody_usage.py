"""Process-local diagnostic counters for outbound Mindbody API calls.

No external requests, persistence, secrets or customer information are recorded.
These counters exclude other servers/apps using the same partner API key.
"""
from __future__ import annotations

from collections import Counter
from threading import Lock
from time import time

_LOCK = Lock()
_BUCKETS: dict[int, Counter[tuple[str, str]]] = {}
_HOURS = 24


def record_call(method: str, endpoint: str) -> None:
    hour = int(time() // 3600)
    key = (str(method).upper(), str(endpoint).strip("/").lower())
    with _LOCK:
        _BUCKETS.setdefault(hour, Counter())[key] += 1
        for old in list(_BUCKETS):
            if old <= hour - _HOURS:
                del _BUCKETS[old]


def snapshot() -> dict:
    hour = int(time() // 3600)
    counts: Counter[tuple[str, str]] = Counter()
    with _LOCK:
        for bucket_hour, values in _BUCKETS.items():
            if hour - _HOURS < bucket_hour <= hour:
                counts.update(values)
    return {
        "scope": "this_server_process_only",
        "window": "rolling_24_hour_buckets",
        "warning": "Not a Mindbody billing total; excludes other processes, credentials and servers.",
        "total": sum(counts.values()),
        "by_endpoint": [
            {"method": method, "endpoint": path, "calls": count}
            for (method, path), count in counts.most_common()
        ],
    }
