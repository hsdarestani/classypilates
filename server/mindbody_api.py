"""Small server-side client for the Mindbody Public API v6.

Only read-only calls are used here. Credentials stay in environment variables and
are never returned or logged.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_API_URL = "https://api.mindbodyonline.com/public/v6"
DEFAULT_SITE_ID = "5742686"
USER_AGENT = "ClassyPilates/1.0"


class MindbodyError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, code: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code


@dataclass(frozen=True)
class MindbodyConfig:
    api_key: str
    site_id: str
    api_url: str = DEFAULT_API_URL

    @classmethod
    def from_env(cls) -> "MindbodyConfig":
        api_key = (os.getenv("MINDBODY_API_KEY") or "").strip()
        site_id = (os.getenv("MINDBODY_SITE_ID") or DEFAULT_SITE_ID).strip()
        api_url = (os.getenv("MINDBODY_API_URL") or DEFAULT_API_URL).strip().rstrip("/")
        if not api_key:
            raise MindbodyError("Mindbody API key is not configured", code="not_configured")
        if not site_id:
            raise MindbodyError("Mindbody site ID is not configured", code="not_configured")
        return cls(api_key=api_key, site_id=site_id, api_url=api_url)


class MindbodyClient:
    def __init__(self, config: MindbodyConfig, timeout: float = 20.0):
        self.config = config
        self.timeout = timeout

    @classmethod
    def from_env(cls, timeout: float = 20.0) -> "MindbodyClient":
        return cls(MindbodyConfig.from_env(), timeout=timeout)

    def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = ""
        if params:
            clean = {key: value for key, value in params.items() if value is not None and value != ""}
            query = "?" + urllib.parse.urlencode(clean, doseq=True) if clean else ""
        url = f"{self.config.api_url}/{path.lstrip('/')}{query}"
        request = urllib.request.Request(
            url,
            headers={
                "API-Key": self.config.api_key,
                "SiteId": self.config.site_id,
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body or "{}")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            code = None
            message = f"Mindbody returned HTTP {exc.code}"
            try:
                payload = json.loads(body)
                error = payload.get("Error") or payload.get("error") or payload
                if isinstance(error, dict):
                    code = error.get("Code") or error.get("code") or error.get("errorCode")
                    detail = error.get("Message") or error.get("message") or error.get("errorMessage")
                    if detail:
                        message = str(detail)
            except Exception:
                pass
            raise MindbodyError(message, status=exc.code, code=code) from exc
        except urllib.error.URLError as exc:
            raise MindbodyError(f"Could not reach Mindbody: {exc.reason}", code="network_error") from exc
        except json.JSONDecodeError as exc:
            raise MindbodyError("Mindbody returned invalid JSON", code="invalid_json") from exc

    def get_sites(self) -> dict[str, Any]:
        return self._request("site/sites")

    def get_locations(self) -> dict[str, Any]:
        return self._request("site/locations")

    def get_classes(
        self,
        *,
        start_date_time: str | None = None,
        end_date_time: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, Any]:
        return self._request(
            "class/classes",
            {
                "StartDateTime": start_date_time,
                "EndDateTime": end_date_time,
                "Limit": limit,
                "Offset": offset,
            },
        )


def _extract_list(payload: Any, names: tuple[str, ...]) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for name in names:
            value = payload.get(name)
            if isinstance(value, list):
                return value
    return []


def safe_connection_summary(client: MindbodyClient | None = None) -> dict[str, Any]:
    client = client or MindbodyClient.from_env()
    locations_payload = client.get_locations()
    classes_payload = client.get_classes()
    locations = _extract_list(locations_payload, ("Locations", "locations", "Items", "items"))
    classes = _extract_list(classes_payload, ("Classes", "classes", "Items", "items"))

    location_names: list[str] = []
    for row in locations[:20]:
        if not isinstance(row, dict):
            continue
        name = row.get("Name") or row.get("name")
        if name:
            location_names.append(str(name))

    return {
        "ok": True,
        "site_id": client.config.site_id,
        "locations": len(locations),
        "classes_default_window": len(classes),
        "location_names": location_names,
    }


def main() -> int:
    try:
        print(json.dumps(safe_connection_summary(), ensure_ascii=False, sort_keys=True))
        return 0
    except MindbodyError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "status": exc.status,
                    "code": exc.code,
                    "message": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
