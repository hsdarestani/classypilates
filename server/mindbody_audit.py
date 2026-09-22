from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

import mindbody_sync as mb
import main as core


def val(row, *names, default=None):
    return mb._value(row, *names, default=default)


def as_int(row, *names):
    value = val(row, *names, default=None)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return None


def expected_available(remote):
    cap = as_int(remote, "MaxCapacity", "Capacity")
    total = as_int(remote, "TotalBooked", "TotalClients")
    if cap is None or total is None:
        return None
    available = max(0, cap - max(0, total))
    web_cap = as_int(remote, "WebCapacity")
    web_booked = as_int(remote, "TotalWebBooked", "WebBooked", "TotalWebClients")
    if web_cap is not None and web_booked is not None:
        available = min(available, max(0, web_cap - max(0, web_booked)))
    return available


def remote_cancelled(remote):
    value = val(remote, "IsCanceled", "IsCancelled", "Cancelled", "isCanceled", "isCancelled", default=False)
    return bool(value)


def main():
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=45)
    client = mb.WriteClient.from_env()

    remotes = []
    offset = 0
    while True:
        payload = client.get_classes(
            start_date_time=now.isoformat(),
            end_date_time=end.isoformat(),
            limit=200,
            offset=offset,
        )
        batch = [x for x in mb._extract_list(payload, ("Classes", "classes", "Items")) if isinstance(x, dict)]
        remotes.extend(batch)
        if len(batch) < 200:
            break
        offset += len(batch)

    issues = Counter()
    samples = []
    with core.SessionLocal() as db:
        local_rows = db.scalars(
            select(core.ClassSession).where(core.ClassSession.mindbody_class_id.is_not(None))
        ).all()
        by_remote = {str(x.mindbody_class_id): x for x in local_rows if x.mindbody_class_id}

        duplicate_ids = db.execute(
            select(core.ClassSession.mindbody_class_id, func.count(core.ClassSession.id))
            .where(core.ClassSession.mindbody_class_id.is_not(None))
            .group_by(core.ClassSession.mindbody_class_id)
            .having(func.count(core.ClassSession.id) > 1)
        ).all()
        issues["duplicate_remote_ids"] = len(duplicate_ids)

        local_ids = [x.id for x in local_rows]
        reserved_counts = {}
        if local_ids:
            reserved_counts = dict(db.execute(
                select(core.Booking.class_id, func.count(core.Booking.id))
                .where(core.Booking.class_id.in_(local_ids), core.Booking.status == "reserved")
                .group_by(core.Booking.class_id)
            ).all())

        seen_remote = set()
        for remote in remotes:
            remote_id = str(val(remote, "Id", "ID", "ClassId", default="") or "")
            if not remote_id:
                continue
            seen_remote.add(remote_id)
            klass = by_remote.get(remote_id)
            if not klass:
                issues["missing_local_class"] += 1
                if len(samples) < 30:
                    samples.append({"type":"missing_local_class","remote_id":remote_id,"title":mb._class_name(remote)})
                continue

            cap = as_int(remote, "MaxCapacity", "Capacity")
            if cap is not None and int(klass.capacity or 0) != cap:
                issues["capacity_mismatch"] += 1
                if len(samples) < 30:
                    samples.append({"type":"capacity_mismatch","remote_id":remote_id,"remote":cap,"local":klass.capacity})

            expected = expected_available(remote)
            if expected is not None:
                local_reserved = int(reserved_counts.get(klass.id, 0)) + int(klass.imported_bookings or 0)
                local_available = max(0, int(klass.capacity or 0) - local_reserved)
                if local_available != expected:
                    issues["availability_mismatch"] += 1
                    if len(samples) < 30:
                        samples.append({"type":"availability_mismatch","remote_id":remote_id,"remote_free":expected,"local_free":local_available})

            remote_start = mb._parse_dt(val(remote, "StartDateTime", "startDateTime"))
            if remote_start and abs((core.as_utc(klass.starts_at) - remote_start).total_seconds()) > 60:
                issues["start_time_mismatch"] += 1
                if len(samples) < 30:
                    samples.append({"type":"start_time_mismatch","remote_id":remote_id,"remote":remote_start.isoformat(),"local":core.as_utc(klass.starts_at).isoformat()})

            remote_studio = mb._remote_class_studio_id(remote)
            if remote_studio and klass.studio_id != remote_studio:
                issues["studio_mismatch"] += 1
                if len(samples) < 30:
                    samples.append({"type":"studio_mismatch","remote_id":remote_id,"remote":remote_studio,"local":klass.studio_id})

            remote_title = mb._class_name(remote)
            if remote_title and (klass.title or "").strip().casefold() != remote_title.strip().casefold():
                issues["title_mismatch"] += 1
                if len(samples) < 30:
                    samples.append({"type":"title_mismatch","remote_id":remote_id,"remote":remote_title,"local":klass.title})

            if remote_start:
                remote_duration = mb._remote_class_duration(remote, remote_start)
                if int(klass.duration or 0) != int(remote_duration):
                    issues["duration_mismatch"] += 1
                    if len(samples) < 30:
                        samples.append({"type":"duration_mismatch","remote_id":remote_id,"remote":remote_duration,"local":klass.duration})

            remote_description = mb._remote_class_description(remote)
            if (klass.description or "").strip() != remote_description.strip():
                issues["description_mismatch"] += 1
                if len(samples) < 30:
                    samples.append({"type":"description_mismatch","remote_id":remote_id})

            should_cancel = remote_cancelled(remote)
            if should_cancel != (klass.status == "cancelled"):
                issues["cancel_status_mismatch"] += 1
                if len(samples) < 30:
                    samples.append({"type":"cancel_status_mismatch","remote_id":remote_id,"remote_cancelled":should_cancel,"local_status":klass.status})

            remote_staff = remote.get("Staff") or remote.get("staff") or {}
            remote_staff_id = mb._remote_staff_id(remote_staff)
            if remote_staff_id:
                local_remote_staff_id = ""
                if klass.coach_id:
                    state = mb._state_row(db, "coach", klass.coach_id)
                    local_remote_staff_id = str((state or {}).get("remote_id") or "")
                if local_remote_staff_id and local_remote_staff_id != remote_staff_id:
                    issues["trainer_mismatch"] += 1
                    if len(samples) < 30:
                        samples.append({"type":"trainer_mismatch","remote_id":remote_id,"remote_staff":remote_staff_id,"local_staff":local_remote_staff_id})

        unlinked_future_classes = db.scalar(select(func.count(core.ClassSession.id)).where(
            core.ClassSession.starts_at >= now,
            core.ClassSession.status == "active",
            core.ClassSession.mindbody_class_id.is_(None),
        )) or 0
        issues["unlinked_future_classes"] = int(unlinked_future_classes)

        waitlist_unsynced = db.scalar(
            select(func.count(core.Waitlist.id))
            .join(core.ClassSession, core.Waitlist.class_id == core.ClassSession.id)
            .where(
                core.ClassSession.mindbody_class_id.is_not(None),
                (
                    core.Waitlist.mindbody_waitlist_entry_id.is_(None)
                    | (core.Waitlist.mindbody_sync_status != "synced")
                ),
            )
        ) or 0
        issues["waitlist_unsynced"] = int(waitlist_unsynced)

        hold_cutoff = now - timedelta(minutes=35)
        stale_pending_holds = db.scalar(
            select(func.count(core.Booking.id))
            .join(core.ClassSession, core.Booking.class_id == core.ClassSession.id)
            .where(
                core.Booking.source == "website",
                core.Booking.status == "reserved",
                core.Booking.payment_status == "pending",
                core.ClassSession.mindbody_class_id.is_not(None),
                core.Booking.created_at < hold_cutoff,
            )
        ) or 0
        issues["stale_pending_holds"] = int(stale_pending_holds)

        paid_unsynced = db.scalar(select(func.count(core.Booking.id)).where(
            core.Booking.source == "website",
            core.Booking.status == "reserved",
            core.Booking.payment_status == "paid",
            core.Booking.mindbody_sync_status != "synced",
        )) or 0
        cancel_failed = db.scalar(select(func.count(core.Booking.id)).where(
            core.Booking.mindbody_sync_status == "cancel_failed"
        )) or 0
        issues["paid_booking_unsynced"] = int(paid_unsynced)
        issues["cancel_failed"] = int(cancel_failed)

    critical_keys = [
        "duplicate_remote_ids","missing_local_class","capacity_mismatch","availability_mismatch",
        "start_time_mismatch","studio_mismatch","title_mismatch","duration_mismatch",
        "description_mismatch","cancel_status_mismatch","trainer_mismatch",
        "unlinked_future_classes","waitlist_unsynced","stale_pending_holds",
        "paid_booking_unsynced","cancel_failed",
    ]
    result = {
        "ok": all(int(issues.get(k, 0)) == 0 for k in critical_keys),
        "remote_classes": len(remotes),
        "issues": {k:int(issues.get(k,0)) for k in critical_keys},
        "samples": samples,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    raise SystemExit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()
