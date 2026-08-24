"""Idempotently import the non-personal Mindbody schedule export."""

from __future__ import annotations

import argparse
import gzip
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from main import ClassSession, Coach, SessionLocal, Studio


DEFAULT_SOURCE = Path(__file__).parent / "data" / "mindbody_schedule_2026-04-01_to_2026-08-24.json.gz"
LOCAL_TIMEZONE = ZoneInfo("Europe/Berlin")


def class_type(title: str) -> str:
    normalized = title.casefold()
    if "powerformer" in normalized:
        return "Powerformer"
    if "reformer" in normalized:
        return "Reformer"
    if "barre" in normalized:
        return "Barre"
    if "mat " in normalized or "mat-" in normalized:
        return "Mat Pilates"
    if "total body" in normalized or "butt & abs" in normalized:
        return "Reformer"
    return "Pilates"


def studio_id(location: str, title: str) -> str | None:
    location_value = location.casefold()
    title_value = title.casefold()
    if "bornheim" in location_value:
        return "bornheim"
    if "sachsenhausen" in location_value:
        return "sachsen"
    if " mid" in f" {location_value}":
        return "mid"
    if "oval" in location_value:
        return "oval"
    if "bahnhofsviertel" in location_value:
        if "2nd floor" in title_value or "ladies" in title_value:
            return "ladies"
        return "bhf1"
    return None


def starts_at(date_value: str, time_value: str) -> datetime:
    local_value = datetime.strptime(f"{date_value} {time_value}", "%Y-%m-%d %H:%M")
    return local_value.replace(tzinfo=LOCAL_TIMEZONE)


def import_schedule(source: Path, dry_run: bool = False) -> dict[str, int]:
    if source.suffix == ".gz":
        with gzip.open(source, "rt", encoding="utf-8") as source_file:
            payload = json.load(source_file)
    else:
        payload = json.loads(source.read_text(encoding="utf-8"))
    class_rows = {row["class_id"]: row for row in payload["classes"]}
    location_rows = {row["location_id"]: row for row in payload["locations"]}
    coach_rows = {row["coach_id"]: row for row in payload["coaches"]}

    counters = {
        "coaches_created": 0,
        "sessions_created": 0,
        "sessions_existing": 0,
        "sessions_skipped": 0,
        "booking_rows_linked": 0,
        "active_seats_linked": 0,
    }

    with SessionLocal() as db:
        coach_ids: dict[str, int] = {}
        for source_id, row in coach_rows.items():
            display_name = str(row.get("display_name") or "").strip()
            if not display_name:
                continue
            coach = db.scalar(
                select(Coach).where(func.lower(Coach.display_name) == display_name.lower())
            )
            if coach is None:
                coach = Coach(display_name=display_name, active=True)
                db.add(coach)
                db.flush()
                counters["coaches_created"] += 1
            coach_ids[source_id] = coach.id

        for row in payload["sessions"]:
            class_row = class_rows.get(row.get("class_id"), {})
            location_row = location_rows.get(row.get("location_id"), {})
            title = str(class_row.get("name") or "").strip()
            location_name = str(location_row.get("name") or "").strip()
            target_studio_id = studio_id(location_name, title)
            if not title or not target_studio_id or not db.get(Studio, target_studio_id):
                counters["sessions_skipped"] += 1
                continue

            source_starts_at = starts_at(str(row["date"]), str(row["start_time"]))
            source_total = max(0, int(row.get("bookings_total") or 0))
            source_active = max(
                0,
                int(row.get("attended_count") or 0)
                + int(row.get("absent_count") or 0)
                + int(row.get("reserved_count") or 0),
            )
            counters["booking_rows_linked"] += source_total
            counters["active_seats_linked"] += source_active
            existing = db.scalar(
                select(ClassSession).where(
                    ClassSession.studio_id == target_studio_id,
                    ClassSession.title == title,
                    ClassSession.starts_at == source_starts_at,
                )
            )
            coach_id = coach_ids.get(str(row.get("coach_id") or ""))
            if existing is not None:
                if existing.coach_id is None and coach_id is not None:
                    existing.coach_id = coach_id
                existing.imported_bookings = source_active
                existing.source_bookings_total = source_total
                if source_active > existing.capacity:
                    existing.capacity = source_active
                counters["sessions_existing"] += 1
                continue

            studio = db.get(Studio, target_studio_id)
            capacity = max(int(class_row.get("capacity") or studio.capacity), source_active)
            duration = row.get("duration_minutes") or class_row.get("default_duration_minutes") or 50
            db.add(
                ClassSession(
                    studio_id=target_studio_id,
                    title=title,
                    class_type=class_type(title),
                    coach_id=coach_id,
                    starts_at=source_starts_at,
                    duration=max(15, int(duration)),
                    capacity=max(1, int(capacity)),
                    imported_bookings=source_active,
                    source_bookings_total=source_total,
                    status="active",
                )
            )
            counters["sessions_created"] += 1

        if dry_run:
            db.rollback()
        else:
            db.commit()

    return counters


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    result = import_schedule(args.source, dry_run=args.dry_run)
    result["dry_run"] = int(args.dry_run)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
