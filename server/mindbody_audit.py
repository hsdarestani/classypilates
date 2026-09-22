from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text

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


def visit_cancelled(visit):
    flags = [
        val(visit, "Cancelled", "IsCancelled", "LateCancelled", "EarlyCancelled", default=False),
    ]
    if any(bool(x) for x in flags):
        return True
    return str(val(visit, "Status", "status", default="") or "").strip().casefold() == "cancelled"


def visit_identity(visit, remote_class_id):
    client_data = visit.get("Client") or visit.get("client") or {}
    visit_id = str(val(visit, "Id", "ID", "VisitId", "VisitID", default="") or "")
    client_id = str(val(
        visit, "ClientId", "ClientID",
        default=val(client_data, "Id", "ID", default=""),
    ) or "")
    return visit_id or f"client:{client_id}:class:{remote_class_id}"


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
            core.ClassSession.starts_at < end,
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
        if stale_pending_holds and len(samples) < 30:
            rows = db.execute(select(
                core.Booking.id,
                core.Booking.reference,
                core.Booking.mindbody_sync_status,
                core.Booking.created_at,
            ).where(
                core.Booking.source == "website",
                core.Booking.status == "reserved",
                core.Booking.payment_status == "pending",
                core.Booking.created_at < hold_cutoff,
            ).limit(5)).all()
            for row in rows:
                samples.append({
                    "type": "stale_pending_hold",
                    "booking_id": row.id,
                    "reference": row.reference,
                    "sync_status": row.mindbody_sync_status,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                })

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
        if paid_unsynced and len(samples) < 30:
            rows = db.execute(select(
                core.Booking.id,
                core.Booking.reference,
                core.Booking.mindbody_sync_status,
                core.Booking.mindbody_sync_error,
            ).where(
                core.Booking.source == "website",
                core.Booking.status == "reserved",
                core.Booking.payment_status == "paid",
                core.Booking.mindbody_sync_status != "synced",
            ).limit(5)).all()
            for row in rows:
                samples.append({
                    "type": "paid_booking_unsynced",
                    "booking_id": row.id,
                    "reference": row.reference,
                    "sync_status": row.mindbody_sync_status,
                    "error": (row.mindbody_sync_error or "")[:300],
                })
        issues["cancel_failed"] = int(cancel_failed)

        # Database-level duplicate / omission audit.
        duplicate_active_website = db.execute(text("""
            SELECT class_id, lower(email) AS email_key, count(*) AS n
            FROM bookings
            WHERE source='website' AND status='reserved'
            GROUP BY class_id, lower(email)
            HAVING count(*) > 1
        """)).all()
        issues["duplicate_active_website_bookings"] = len(duplicate_active_website)

        duplicate_active_spots = db.execute(text("""
            SELECT class_id, spot_number, count(*) AS n
            FROM bookings
            WHERE status='reserved' AND spot_number IS NOT NULL
            GROUP BY class_id, spot_number
            HAVING count(*) > 1
        """)).all()
        issues["duplicate_active_spots"] = len(duplicate_active_spots)

        duplicate_visit_ids = db.execute(text("""
            SELECT mindbody_visit_id, count(*) AS n
            FROM bookings
            WHERE mindbody_visit_id IS NOT NULL AND mindbody_visit_id <> ''
            GROUP BY mindbody_visit_id
            HAVING count(*) > 1
        """)).all()
        issues["duplicate_mindbody_visit_ids"] = len(duplicate_visit_ids)

        duplicate_waitlist = db.execute(text("""
            SELECT class_id, lower(email) AS email_key, count(*) AS n
            FROM waitlist
            GROUP BY class_id, lower(email)
            HAVING count(*) > 1
        """)).all()
        issues["duplicate_waitlist_entries"] = len(duplicate_waitlist)

        duplicate_waitlist_remote = db.execute(text("""
            SELECT mindbody_waitlist_entry_id, count(*) AS n
            FROM waitlist
            WHERE mindbody_waitlist_entry_id IS NOT NULL AND mindbody_waitlist_entry_id <> ''
            GROUP BY mindbody_waitlist_entry_id
            HAVING count(*) > 1
        """)).all()
        issues["duplicate_waitlist_remote_ids"] = len(duplicate_waitlist_remote)

        duplicate_paid_orders = db.execute(text("""
            SELECT booking_reference, count(*) AS n
            FROM payment_orders
            WHERE booking_reference IS NOT NULL AND status='paid'
            GROUP BY booking_reference
            HAVING count(*) > 1
        """)).all()
        issues["multiple_paid_orders_per_booking"] = len(duplicate_paid_orders)

        paid_order_without_booking = db.execute(text("""
            SELECT po.reference
            FROM payment_orders po
            LEFT JOIN bookings b ON b.reference = po.booking_reference
            WHERE po.status='paid' AND po.booking_reference IS NOT NULL AND b.id IS NULL
            LIMIT 50
        """)).all()
        issues["paid_order_without_booking"] = len(paid_order_without_booking)

        paid_sumup_without_order = db.execute(text("""
            SELECT b.reference
            FROM bookings b
            LEFT JOIN payment_orders po
              ON po.booking_reference=b.reference AND po.status='paid'
            WHERE b.payment_status='paid' AND b.payment_method='sumup'
            GROUP BY b.reference
            HAVING count(po.id)=0
        """)).all()
        issues["paid_sumup_booking_without_paid_order"] = len(paid_sumup_without_order)

        duplicate_active_coach_names = db.execute(text("""
            SELECT lower(regexp_replace(trim(display_name), '\\s+', ' ', 'g')) AS name_key, count(*) AS n
            FROM coaches
            WHERE active=true
            GROUP BY lower(regexp_replace(trim(display_name), '\\s+', ' ', 'g'))
            HAVING count(*) > 1
        """)).all() if core.engine.dialect.name != "sqlite" else []
        issues["duplicate_active_coach_names"] = len(duplicate_active_coach_names)

        duplicate_coach_remote_map = db.execute(text("""
            SELECT remote_id, count(*) AS n
            FROM mindbody_sync_state
            WHERE entity_type='coach' AND remote_id IS NOT NULL AND remote_id <> ''
            GROUP BY remote_id
            HAVING count(*) > 1
        """)).all()
        issues["duplicate_coach_remote_mapping"] = len(duplicate_coach_remote_map)

        # Compare individual active Mindbody visits against local rows for the near-term
        # schedule. This catches both "booking missing in Classy" and "booking exists
        # locally but no longer exists in Mindbody".
        roster_until = now + timedelta(days=7)
        remote_visits_missing_local = 0
        local_visits_missing_remote = 0
        roster_audit_errors = 0
        roster_classes_checked = 0

        near_remote = []
        for remote in remotes:
            starts = mb._parse_dt(val(remote, "StartDateTime", "startDateTime"))
            if starts and now <= starts < roster_until and not remote_cancelled(remote):
                near_remote.append(remote)

        for remote in near_remote:
            remote_id = str(val(remote, "Id", "ID", "ClassId", default="") or "")
            if not remote_id:
                continue
            klass = by_remote.get(remote_id)
            if not klass:
                continue
            try:
                payload = client.get_class_visits(remote_id)
            except Exception as exc:
                roster_audit_errors += 1
                if len(samples) < 30:
                    samples.append({"type":"roster_audit_error","remote_id":remote_id,"error":str(exc)[:200]})
                continue

            roster_classes_checked += 1
            visits = [
                row for row in mb._extract_list(payload, ("Visits", "visits", "ClassVisits", "Items"))
                if isinstance(row, dict) and not visit_cancelled(row)
            ]
            remote_active_ids = {visit_identity(row, remote_id) for row in visits}
            local_active_ids = {
                str(value) for value in db.scalars(
                    select(core.Booking.mindbody_visit_id).where(
                        core.Booking.class_id == klass.id,
                        core.Booking.status == "reserved",
                        core.Booking.mindbody_visit_id.is_not(None),
                    )
                ).all() if value
            }
            missing_local = remote_active_ids - local_active_ids
            missing_remote = local_active_ids - remote_active_ids
            remote_visits_missing_local += len(missing_local)
            local_visits_missing_remote += len(missing_remote)
            if missing_local and len(samples) < 30:
                samples.append({
                    "type":"remote_visits_missing_local",
                    "remote_id":remote_id,
                    "count":len(missing_local),
                    "visit_ids":sorted(missing_local)[:5],
                })
            if missing_remote and len(samples) < 30:
                samples.append({
                    "type":"local_visits_missing_remote",
                    "remote_id":remote_id,
                    "count":len(missing_remote),
                    "visit_ids":sorted(missing_remote)[:5],
                })

        issues["remote_visits_missing_local"] = remote_visits_missing_local
        issues["local_visits_missing_remote"] = local_visits_missing_remote
        issues["roster_audit_errors"] = roster_audit_errors
        issues["roster_classes_checked"] = roster_classes_checked

    critical_keys = [
        "duplicate_remote_ids","missing_local_class","capacity_mismatch","availability_mismatch",
        "start_time_mismatch","studio_mismatch","title_mismatch","duration_mismatch",
        "description_mismatch","cancel_status_mismatch","trainer_mismatch",
        "unlinked_future_classes","waitlist_unsynced","stale_pending_holds",
        "paid_booking_unsynced","cancel_failed",
        "duplicate_active_website_bookings","duplicate_active_spots",
        "duplicate_mindbody_visit_ids","duplicate_waitlist_entries",
        "duplicate_waitlist_remote_ids","multiple_paid_orders_per_booking",
        "paid_order_without_booking","paid_sumup_booking_without_paid_order",
        "duplicate_active_coach_names","duplicate_coach_remote_mapping",
        "remote_visits_missing_local","local_visits_missing_remote","roster_audit_errors",
    ]
    result = {
        "ok": all(int(issues.get(k, 0)) == 0 for k in critical_keys),
        "remote_classes": len(remotes),
        "roster_classes_checked": int(issues.get("roster_classes_checked", 0)),
        "issues": {k:int(issues.get(k,0)) for k in critical_keys},
        "samples": samples,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    raise SystemExit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()
