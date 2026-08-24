"""Idempotently import the non-personal Mindbody schedule export."""

from __future__ import annotations

import argparse
import gzip
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import MetaData, Table, create_engine, inspect, select, text


DEFAULT_SOURCE = Path(__file__).parent / "data" / "mindbody_schedule_2026-04-01_to_2026-08-24.json.gz"
LOCAL_TIMEZONE = ZoneInfo("Europe/Berlin")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/classy.db")


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


def normalized_start(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=LOCAL_TIMEZONE)
    return value.astimezone(timezone.utc).replace(microsecond=0)


def ensure_schema(engine) -> None:
    columns = {column["name"] for column in inspect(engine).get_columns("classes")}
    with engine.begin() as connection:
        if "imported_bookings" not in columns:
            connection.execute(text("ALTER TABLE classes ADD COLUMN imported_bookings INTEGER NOT NULL DEFAULT 0"))
        if "source_bookings_total" not in columns:
            connection.execute(text("ALTER TABLE classes ADD COLUMN source_bookings_total INTEGER NOT NULL DEFAULT 0"))


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

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    ensure_schema(engine)
    metadata = MetaData()
    studios = Table("studios", metadata, autoload_with=engine)
    coaches = Table("coaches", metadata, autoload_with=engine)
    sessions = Table("classes", metadata, autoload_with=engine)

    connection = engine.connect()
    transaction = connection.begin()
    try:
        studio_rows = {row["id"]: row for row in connection.execute(select(studios)).mappings()}
        existing_coaches = {
            str(row["display_name"]).strip().casefold(): row["id"]
            for row in connection.execute(select(coaches.c.id, coaches.c.display_name)).mappings()
        }
        coach_ids: dict[str, int] = {}
        for source_id, row in coach_rows.items():
            display_name = str(row.get("display_name") or "").strip()
            if not display_name:
                continue
            coach_id = existing_coaches.get(display_name.casefold())
            if coach_id is None:
                result = connection.execute(coaches.insert().values(
                    user_id=None, display_name=display_name, photo_url="", bio="", active=True,
                ))
                coach_id = int(result.inserted_primary_key[0])
                existing_coaches[display_name.casefold()] = coach_id
                counters["coaches_created"] += 1
            coach_ids[source_id] = coach_id

        existing_sessions = {}
        for existing in connection.execute(select(
            sessions.c.id, sessions.c.studio_id, sessions.c.title, sessions.c.starts_at,
            sessions.c.coach_id, sessions.c.capacity,
        )).mappings():
            key = (existing["studio_id"], existing["title"], normalized_start(existing["starts_at"]))
            existing_sessions[key] = existing

        for row in payload["sessions"]:
            class_row = class_rows.get(row.get("class_id"), {})
            location_row = location_rows.get(row.get("location_id"), {})
            title = str(class_row.get("name") or "").strip()
            location_name = str(location_row.get("name") or "").strip()
            target_studio_id = studio_id(location_name, title)
            if not title or not target_studio_id or target_studio_id not in studio_rows:
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
            existing = existing_sessions.get((target_studio_id, title, normalized_start(source_starts_at)))
            coach_id = coach_ids.get(str(row.get("coach_id") or ""))
            if existing is not None:
                values = {
                    "imported_bookings": source_active,
                    "source_bookings_total": source_total,
                    "capacity": max(int(existing["capacity"] or 1), source_active),
                }
                if existing["coach_id"] is None and coach_id is not None:
                    values["coach_id"] = coach_id
                connection.execute(sessions.update().where(sessions.c.id == existing["id"]).values(**values))
                counters["sessions_existing"] += 1
                continue

            studio = studio_rows[target_studio_id]
            capacity = max(int(class_row.get("capacity") or studio["capacity"]), source_active)
            duration = row.get("duration_minutes") or class_row.get("default_duration_minutes") or 50
            result = connection.execute(sessions.insert().values(
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
                created_by=None,
            ))
            inserted_id = int(result.inserted_primary_key[0])
            existing_sessions[(target_studio_id, title, normalized_start(source_starts_at))] = {
                "id": inserted_id, "coach_id": coach_id, "capacity": capacity,
            }
            counters["sessions_created"] += 1

        if dry_run:
            transaction.rollback()
        else:
            transaction.commit()
    except Exception:
        transaction.rollback()
        raise
    finally:
        connection.close()
        engine.dispose()

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
