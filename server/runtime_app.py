import os

import feedback_app as feedback
import class_language  # registers DE/EN class-language routes and payloads
import mindbody_sync  # registers the production two-way booking mirror

app = feedback.app


def _prefer_latest_routes() -> None:
    """Keep the newest handler when transitional modules register the same route.

    main.py still contains the legacy booking/class handlers while feedback_app.py
    registers their production V2 replacements on the same FastAPI instance. Starlette
    matches routes in registration order, so without this normalization the legacy
    handler can shadow the newer SumUp/Mindbody-aware implementation.
    """
    seen: set[tuple[str, frozenset[str]]] = set()
    kept = []
    for route in reversed(app.router.routes):
        path = getattr(route, "path", None)
        methods = frozenset(getattr(route, "methods", set()) or set())
        if not path or not methods:
            kept.append(route)
            continue
        key = (path, methods)
        if key in seen:
            continue
        seen.add(key)
        kept.append(route)
    app.router.routes[:] = list(reversed(kept))


def _assert_production_booking_route() -> None:
    matches = [
        route
        for route in app.router.routes
        if getattr(route, "path", None) == "/api/bookings"
        and "POST" in (getattr(route, "methods", set()) or set())
    ]
    if len(matches) != 1 or getattr(matches[0].endpoint, "__name__", "") != "public_booking_v2":
        raise RuntimeError("Production /api/bookings route is not the SumUp/Mindbody-aware V2 handler")


_prefer_latest_routes()
_assert_production_booking_route()


@app.get('/api/capabilities')
def capabilities():
    return {
        'ok': True,
        'instant_email_notifications': bool(os.getenv('SMTP_HOST')),
        'branded_html_email': True,
        'sepa_provider_credentials': bool(os.getenv('SEPA_PROVIDER_KEY')),
        'booking_languages': ['de', 'en'],
        'class_languages': ['de', 'en'],
        'credit_packs': [1, 5, 10, 20, 30, 50],
        'class_recurrence': 'monthly',
        'monthly_memberships': True,
        'mindbody_mirror': mindbody_sync.capability_status(),
    }
