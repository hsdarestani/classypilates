"""Mindbody webhook receiver, durable event queue, and subscription tooling.

Webhook payloads are treated as invalidation signals. We persist/dedupe them first,
acknowledge quickly, then re-read current provider state so duplicate or out-of-order
notifications cannot corrupt booking or capacity counters.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Request, Response
from sqlalchemy import select, text

import main as core
import mindbody_sync


# External production URL is configured by deploy-production.yml and resolves
# through the Strato host at new.classypilates.de.
WEBHOOK_PATH = "/api/integrations/mindbody/webhook"
SUBSCRIPTION_REFERENCE = "classypilates-production-webhooks-v1"
PUSH_API_BASE = "https://mb-api.mindbodyonline.com/push/api/v1"
USER_AGENT = "ClassyPilates/1.0"
EVENT_IDS = (
    "classRosterBooking.created",
    "classRosterBookingStatus.updated",
    "classRosterBooking.cancelled",
    "classWaitlistRequest.created",
    "classWaitlistRequest.cancelled",
    "class.updated",
    "classSchedule.created",
    "classSchedule.updated",
    "classSchedule.cancelled",
    "classDescription.updated",
)
MAX_ATTEMPTS = max(8, int(os.getenv("MINDBODY_WEBHOOK_MAX_ATTEMPTS", "20")))
DEBOUNCE_SECONDS = max(0.25, float(os.getenv("MINDBODY_WEBHOOK_DEBOUNCE_SECONDS", "1.0")))
WORKER_IDLE_SECONDS = max(0.5, float(os.getenv("MINDBODY_WEBHOOK_WORKER_IDLE_SECONDS", "1.0")))

_worker_started = False
_worker_guard = threading.Lock()


def webhook_status() -> dict[str, Any]:
    return {
        "configured": bool((os.getenv("MINDBODY_WEBHOOK_SIGNATURE_KEY") or "").strip()),
        "subscription_configured": bool((os.getenv("MINDBODY_WEBHOOK_SUBSCRIPTION_ID") or "").strip()),
        "path": WEBHOOK_PATH,
        "events": len(EVENT_IDS),
        "durable_queue": True,
        "deduplicated": True,
    }


def _ensure_event_store(*, reset_processing: bool = False) -> None:
    timestamp_type = "DATETIME" if core.engine.dialect.name == "sqlite" else "TIMESTAMP WITH TIME ZONE"
    with core.engine.begin() as connection:
        connection.execute(text(f"""
            CREATE TABLE IF NOT EXISTS mindbody_webhook_events (
                message_id VARCHAR(160) PRIMARY KEY,
                event_id VARCHAR(100) NOT NULL,
                class_id VARCHAR(100),
                payload TEXT NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT NOT NULL DEFAULT '',
                created_at {timestamp_type} NOT NULL,
                next_attempt_at {timestamp_type},
                processed_at {timestamp_type}
            )
        """))
        connection.execute(text("""
            CREATE INDEX IF NOT EXISTS ix_mindbody_webhook_events_pending
            ON mindbody_webhook_events (status, next_attempt_at, created_at)
        """))
        if reset_processing:
            connection.execute(
                text("""
                    UPDATE mindbody_webhook_events
                    SET status='failed',
                        last_error=CASE
                            WHEN last_error='' THEN 'worker_restarted_during_processing'
                            ELSE last_error
                        END
                    WHERE status='processing'
                """)
            )


def _signature_is_valid(raw_body: bytes, supplied: str) -> bool:
    key = (os.getenv("MINDBODY_WEBHOOK_SIGNATURE_KEY") or "").strip()
    if not key or not supplied:
        return False
    digest = hmac.new(key.encode("utf-8"), raw_body, hashlib.sha256).digest()
    expected = "sha256=" + base64.b64encode(digest).decode("ascii")
    return hmac.compare_digest(expected, supplied.strip())


def _event_class_id(payload: dict[str, Any]) -> str:
    data = payload.get("eventData") or {}
    class_id = str(data.get("classId") or "").strip()
    if class_id:
        return class_id

    # classWaitlistRequest.cancelled contains only waitlistEntryId. Resolve its
    # local class when possible so the event still coalesces with the same class.
    entry_id = str(data.get("waitlistEntryId") or "").strip()
    if entry_id:
        with core.SessionLocal() as db:
            row = db.scalar(
                select(core.Waitlist)
                .where(core.Waitlist.mindbody_waitlist_entry_id == entry_id)
                .limit(1)
            )
            if row and row.klass and row.klass.mindbody_class_id:
                return str(row.klass.mindbody_class_id)
    return ""


def _event_start_hint(payload: dict[str, Any]) -> str | None:
    data = payload.get("eventData") or {}
    for key in ("classStartDateTime", "classDateTime", "startDateTime"):
        value = str(data.get(key) or "").strip()
        if value:
            return value
    return None


def _enqueue(payload: dict[str, Any], raw_body: bytes) -> None:
    message_id = str(payload.get("messageId") or "").strip()
    if not message_id:
        message_id = "body:" + hashlib.sha256(raw_body).hexdigest()
    event_id = str(payload.get("eventId") or "").strip()[:100]
    if not event_id:
        return

    now = datetime.now(timezone.utc)
    with core.engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO mindbody_webhook_events
                    (message_id, event_id, class_id, payload, status, attempts, last_error, created_at)
                VALUES
                    (:message_id, :event_id, :class_id, :payload, 'pending', 0, '', :created_at)
                ON CONFLICT (message_id) DO NOTHING
            """),
            {
                "message_id": message_id[:160],
                "event_id": event_id,
                "class_id": _event_class_id(payload)[:100] or None,
                "payload": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                "created_at": now,
            },
        )


def _claim_batch() -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    ready_before = now - timedelta(seconds=DEBOUNCE_SECONDS)
    with core.engine.begin() as connection:
        row = connection.execute(
            text("""
                SELECT message_id, event_id, class_id, payload, attempts, created_at
                FROM mindbody_webhook_events
                WHERE status IN ('pending', 'failed')
                  AND attempts < :max_attempts
                  AND created_at <= :ready_before
                  AND (next_attempt_at IS NULL OR next_attempt_at <= :now)
                ORDER BY created_at ASC
                LIMIT 1
            """),
            {
                "max_attempts": MAX_ATTEMPTS,
                "ready_before": ready_before,
                "now": now,
            },
        ).mappings().first()
        if not row:
            return []

        if row.get("class_id"):
            rows = connection.execute(
                text("""
                    SELECT message_id, event_id, class_id, payload, attempts, created_at
                    FROM mindbody_webhook_events
                    WHERE status IN ('pending', 'failed')
                      AND attempts < :max_attempts
                      AND class_id = :class_id
                      AND created_at <= :ready_before
                      AND (next_attempt_at IS NULL OR next_attempt_at <= :now)
                    ORDER BY created_at ASC
                    LIMIT 100
                """),
                {
                    "max_attempts": MAX_ATTEMPTS,
                    "class_id": row["class_id"],
                    "ready_before": ready_before,
                    "now": now,
                },
            ).mappings().all()
        else:
            rows = [row]

        claimed: list[dict[str, Any]] = []
        for item in rows:
            updated = connection.execute(
                text("""
                    UPDATE mindbody_webhook_events
                    SET status='processing', attempts=attempts+1, last_error=''
                    WHERE message_id=:message_id
                      AND status IN ('pending', 'failed')
                """),
                {"message_id": item["message_id"]},
            )
            if updated.rowcount:
                claimed.append(dict(item))
        return claimed


def _mark_done(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    now = datetime.now(timezone.utc)
    with core.engine.begin() as connection:
        for row in rows:
            connection.execute(
                text("""
                    UPDATE mindbody_webhook_events
                    SET status='done', last_error='', processed_at=:processed_at, next_attempt_at=NULL
                    WHERE message_id=:message_id
                """),
                {"message_id": row["message_id"], "processed_at": now},
            )


def _mark_failed(rows: list[dict[str, Any]], error: Exception) -> None:
    if not rows:
        return
    now = datetime.now(timezone.utc)
    highest_attempt = max(int(row.get("attempts") or 0) + 1 for row in rows)
    delay_seconds = min(300, max(2, 2 ** min(highest_attempt, 8)))
    next_attempt = now + timedelta(seconds=delay_seconds)
    message = f"{type(error).__name__}: {str(error)}"[:1500]
    with core.engine.begin() as connection:
        for row in rows:
            connection.execute(
                text("""
                    UPDATE mindbody_webhook_events
                    SET status='failed', last_error=:last_error, next_attempt_at=:next_attempt_at
                    WHERE message_id=:message_id
                """),
                {
                    "message_id": row["message_id"],
                    "last_error": message,
                    "next_attempt_at": next_attempt,
                },
            )


def _process_batch(rows: list[dict[str, Any]]) -> None:
    payloads = [json.loads(str(row["payload"])) for row in rows]
    class_id = str(rows[0].get("class_id") or "").strip()

    if class_id:
        event_ids = {str(payload.get("eventId") or "") for payload in payloads}
        reconcile_roster = any(event_id.startswith("classRosterBooking.") for event_id in event_ids)
        reconcile_waitlist = any(event_id.startswith("classWaitlistRequest.") for event_id in event_ids)
        sync_coach = "class.updated" in event_ids
        start_hint = next(
            (hint for hint in (_event_start_hint(payload) for payload in payloads) if hint),
            None,
        )
        mindbody_sync.reconcile_remote_class(
            class_id,
            start_hint=start_hint,
            reconcile_roster=reconcile_roster,
            reconcile_waitlist=reconcile_waitlist,
            sync_coach=sync_coach,
        )
        return

    # Schedule/description changes have no individual class ID. They are rare and
    # use the canonical bounded fast sync rather than guessing affected classes.
    with mindbody_sync.RECONCILE_LOCK:
        mindbody_sync.sync_from_mindbody()
        mindbody_sync.retry_pending()


def _cleanup_old_events() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    with core.engine.begin() as connection:
        connection.execute(
            text("""
                DELETE FROM mindbody_webhook_events
                WHERE status='done' AND processed_at IS NOT NULL AND processed_at < :cutoff
            """),
            {"cutoff": cutoff},
        )


def _worker_loop() -> None:
    last_cleanup = 0.0
    while True:
        rows: list[dict[str, Any]] = []
        try:
            rows = _claim_batch()
            if rows:
                _process_batch(rows)
                _mark_done(rows)
            else:
                time.sleep(WORKER_IDLE_SECONDS)

            if time.monotonic() - last_cleanup > 3600:
                _cleanup_old_events()
                last_cleanup = time.monotonic()
        except Exception as exc:
            _mark_failed(rows, exc)
            print(
                f"Mindbody webhook worker failed: {type(exc).__name__}: {str(exc)[:300]}",
                flush=True,
            )
            time.sleep(WORKER_IDLE_SECONDS)


def install(app) -> None:
    @app.head(WEBHOOK_PATH)
    def mindbody_webhook_head():
        # Mindbody validates webhook URLs with HEAD before a subscription is
        # activated. No signature is expected for this URL validation request.
        return Response(status_code=204)

    @app.get(WEBHOOK_PATH)
    def mindbody_webhook_probe():
        # A harmless public probe makes reverse-proxy/domain diagnostics explicit.
        # Event delivery still happens only through signed POST requests below.
        return Response(status_code=204)

    @app.post(WEBHOOK_PATH)
    async def mindbody_webhook_post(request: Request):
        raw_body = await request.body()
        signature_key = (os.getenv("MINDBODY_WEBHOOK_SIGNATURE_KEY") or "").strip()
        signature = request.headers.get("X-Mindbody-Signature", "")

        # Never process unsigned events. A missing key means provisioning has not
        # completed yet; subscriptions remain PendingActivation until the key is
        # stored and the API container is restarted.
        if not signature_key or not _signature_is_valid(raw_body, signature):
            return Response(status_code=400)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception:
            return Response(status_code=400)
        if not isinstance(payload, dict):
            return Response(status_code=400)

        data = payload.get("eventData") or {}
        configured_site = str(os.getenv("MINDBODY_SITE_ID") or "").strip()
        incoming_site = str(data.get("siteId") or "").strip()
        if configured_site and incoming_site and incoming_site != configured_site:
            # A validly signed event for another site should not cause retries or
            # contaminate this tenant's data.
            return Response(status_code=204)

        _enqueue(payload, raw_body)
        return Response(status_code=204)

    @app.on_event("startup")
    def start_mindbody_webhook_worker():
        global _worker_started
        _ensure_event_store(reset_processing=True)
        if not mindbody_sync.SYNC_ENABLED:
            return
        with _worker_guard:
            if _worker_started:
                return
            _worker_started = True
            threading.Thread(
                target=_worker_loop,
                name="mindbody-webhook-worker",
                daemon=True,
            ).start()


def _push_request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    api_key = (os.getenv("MINDBODY_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("MINDBODY_API_KEY is not configured")

    body = None
    headers = {
        "API-Key": api_key,
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        f"{PUSH_API_BASE}/{path.lstrip('/')}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Mindbody Webhooks API HTTP {exc.code}: {raw[:1200]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Mindbody Webhooks API unavailable: {exc.reason}") from exc


def _response_value(payload: Any, *names: str, default: Any = "") -> Any:
    """Read Mindbody Webhooks fields across camelCase/PascalCase responses."""
    if not isinstance(payload, dict):
        return default
    wanted = {str(name).casefold() for name in names}
    for key, value in payload.items():
        if str(key).casefold() in wanted:
            return value
    return default


def _subscriptions() -> list[dict[str, Any]]:
    payload = _push_request("GET", "subscriptions")
    items = payload.get("items") or payload.get("Items") or []
    return [row for row in items if isinstance(row, dict)]


def prepare_subscription(webhook_url: str) -> dict[str, Any]:
    existing_id = (os.getenv("MINDBODY_WEBHOOK_SUBSCRIPTION_ID") or "").strip()
    key_present = bool((os.getenv("MINDBODY_WEBHOOK_SIGNATURE_KEY") or "").strip())

    # When both values are persisted, preserve the exact subscription/key pair.
    # The activation step updates its URL/events/status and will surface an invalid
    # ID without silently pairing the old signature key with another subscription.
    if existing_id and key_present:
        return {
            "subscription_id": existing_id,
            "status": "Existing",
            "signature_key": "",
            "created": False,
        }

    # If either half of the pair was lost, deactivate all subscriptions previously
    # managed by Classy and create a fresh PendingActivation subscription. DELETE
    # deactivates rather than removes subscriptions in Mindbody, so activation
    # always uses the exact new ID returned below instead of searching by reference.
    try:
        for row in _subscriptions():
            reference = str(_response_value(row, "referenceId", "ReferenceId") or "")
            subscription_id = str(_response_value(row, "subscriptionId", "SubscriptionId") or "").strip()
            if reference.startswith(SUBSCRIPTION_REFERENCE) and subscription_id:
                try:
                    _push_request("DELETE", f"subscriptions/{subscription_id}")
                except Exception:
                    pass
    except Exception:
        # Listing old subscriptions is cleanup only. POST below remains the source
        # of truth for the new key/ID pair.
        pass

    unique_reference = (
        f"{SUBSCRIPTION_REFERENCE}:"
        f"{str(os.getenv('MINDBODY_SITE_ID') or 'site')}:"
        f"{int(time.time())}"
    )
    created = _push_request(
        "POST",
        "subscriptions",
        {
            "eventIds": list(EVENT_IDS),
            "eventSchemaVersion": 1,
            "referenceId": unique_reference,
            "webhookUrl": webhook_url,
        },
    )
    subscription_id = str(_response_value(created, "subscriptionId", "SubscriptionId") or "").strip()
    signature_key = str(_response_value(created, "messageSignatureKey", "MessageSignatureKey") or "").strip()
    if not subscription_id or not signature_key:
        raise RuntimeError("Mindbody did not return a webhook subscription ID/signature key")
    return {
        "subscription_id": subscription_id,
        "status": str(_response_value(created, "status", "Status") or ""),
        "signature_key": signature_key,
        "created": True,
    }


def activate_subscription(webhook_url: str, subscription_id: str | None = None) -> dict[str, Any]:
    subscription_id = str(
        subscription_id
        or os.getenv("MINDBODY_WEBHOOK_SUBSCRIPTION_ID")
        or ""
    ).strip()
    if not subscription_id:
        raise RuntimeError("MINDBODY_WEBHOOK_SUBSCRIPTION_ID is not configured")

    updated = _push_request(
        "PATCH",
        f"subscriptions/{subscription_id}",
        {
            "eventIds": list(EVENT_IDS),
            "eventSchemaVersion": 1,
            "webhookUrl": webhook_url,
            "status": "Active",
        },
    )
    return {
        "subscription_id": subscription_id,
        "status": str(_response_value(updated, "status", "Status") or ""),
        "webhook_url": str(_response_value(updated, "webhookUrl", "WebhookUrl") or webhook_url),
        "events": len(_response_value(updated, "eventIds", "EventIds", default=[]) or EVENT_IDS),
    }


def _main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--webhook-url", required=True)
    activate = sub.add_parser("activate")
    activate.add_argument("--webhook-url", required=True)
    activate.add_argument("--subscription-id", default="")
    args = parser.parse_args()

    if args.command == "prepare":
        result = prepare_subscription(args.webhook_url)
    else:
        result = activate_subscription(args.webhook_url, args.subscription_id)
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
