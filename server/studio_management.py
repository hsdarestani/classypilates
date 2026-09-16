from __future__ import annotations

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

import feedback_app as feedback
import main as core

app = feedback.app


class StudioProfile(core.Base):
    __tablename__ = "studio_profiles"

    studio_id: Mapped[str] = mapped_column(ForeignKey("studios.id", ondelete="CASCADE"), primary_key=True)
    name_override: Mapped[str | None] = mapped_column(String(160), nullable=True, default=None)
    address_override: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    capacity_override: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    short_name: Mapped[str] = mapped_column(String(160), default="")
    public_type: Mapped[str] = mapped_column(String(160), default="")
    image_url: Mapped[str] = mapped_column(String(800), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


core.Base.metadata.create_all(core.engine, tables=[StudioProfile.__table__])


STUDIO_DEFAULTS = {
    "bhf1": {
        "short_name": "Bahnhofsviertel 1F",
        "public_type": "Reformer",
        "image_url": "https://classypilates.de/wp-content/uploads/2026/05/Bahnhofviertel_01-scaled.jpg",
        "sort_order": 10,
        "mindbody_location": "Bahnhofsviertel",
    },
    "ladies": {
        "short_name": "Ladies 2F",
        "public_type": "Reformer · Ladies only",
        "image_url": "https://classypilates.de/wp-content/uploads/2026/05/Ladies_02-scaled.jpg",
        "sort_order": 20,
        "mindbody_location": "Bahnhofsviertel · Ladies / 2nd floor",
    },
    "sachsen": {
        "short_name": "Sachsenhausen",
        "public_type": "Reformer · Mat",
        "image_url": "https://classypilates.de/wp-content/uploads/2026/06/IMG_2751-scaled.jpeg",
        "sort_order": 30,
        "mindbody_location": "Sachsenhausen",
    },
    "bornheim": {
        "short_name": "Bornheim",
        "public_type": "Reformer",
        "image_url": "https://classypilates.de/wp-content/uploads/2026/05/Bornheim_07-scaled.jpg",
        "sort_order": 40,
        "mindbody_location": "Bornheim",
    },
    "mid": {
        "short_name": "Mid",
        "public_type": "Powerformer",
        "image_url": "https://classypilates.de/wp-content/uploads/2026/05/Mid_03-scaled.jpg",
        "sort_order": 50,
        "mindbody_location": "Mid",
    },
    "oval": {
        "short_name": "Oval",
        "public_type": "Powerformer",
        "image_url": "https://classypilates.de/wp-content/uploads/2026/05/Oval_01-scaled.jpg",
        "sort_order": 60,
        "mindbody_location": "Oval",
    },
}


class StudioUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    address: str = Field(default="", max_length=255)
    capacity: int = Field(default=10, ge=1, le=100)
    short_name: str = Field(default="", max_length=160)
    public_type: str = Field(default="", max_length=160)
    image_url: str = Field(default="", max_length=800)
    description: str = Field(default="", max_length=3000)
    sort_order: int = Field(default=0, ge=0, le=10000)


def _profile(db: Session, studio_id: str) -> StudioProfile | None:
    return db.get(StudioProfile, studio_id)


def _restore_studio_overrides() -> None:
    """Re-apply admin edits after the legacy seed has populated canonical studios."""
    with core.SessionLocal() as db:
        changed = False
        for profile in db.scalars(select(StudioProfile)).all():
            studio = db.get(core.Studio, profile.studio_id)
            if not studio:
                continue
            if profile.name_override is not None:
                studio.name = profile.name_override
                changed = True
            if profile.address_override is not None:
                studio.address = profile.address_override
                changed = True
            if profile.capacity_override is not None and profile.capacity_override > 0:
                studio.capacity = profile.capacity_override
                changed = True
        if changed:
            db.commit()


_restore_studio_overrides()


def studio_dict(studio: core.Studio, db: Session) -> dict:
    defaults = STUDIO_DEFAULTS.get(studio.id, {})
    profile = _profile(db, studio.id)

    def value(name: str, fallback=""):
        current = getattr(profile, name, None) if profile else None
        if current not in (None, ""):
            return current
        return defaults.get(name, fallback)

    return {
        "id": studio.id,
        "name": profile.name_override if profile and profile.name_override is not None else studio.name,
        "address": profile.address_override if profile and profile.address_override is not None else (studio.address or ""),
        "capacity": int(profile.capacity_override if profile and profile.capacity_override is not None and profile.capacity_override > 0 else (studio.capacity or 1)),
        "short_name": value("short_name", studio.name),
        "public_type": value("public_type", "Pilates"),
        "image_url": value("image_url", ""),
        "description": getattr(profile, "description", "") if profile else "",
        "sort_order": int(value("sort_order", 999) or 999),
        "mindbody_location": defaults.get("mindbody_location", studio.id),
        "mindbody_managed": False,
    }


def _all_studios(db: Session) -> list[dict]:
    rows = db.scalars(select(core.Studio)).all()
    payload = [studio_dict(row, db) for row in rows]
    payload.sort(key=lambda row: (row["sort_order"], row["name"].casefold()))
    return payload


@app.get("/api/studios")
def public_studios(db: Session = Depends(core.db_session)):
    """Canonical public studio metadata used by the website."""
    return {"studios": _all_studios(db)}


@app.get("/api/staff/studios")
def staff_studios(
    user: core.User = Depends(core.require("classes.view")),
    db: Session = Depends(core.db_session),
):
    return {
        "studios": _all_studios(db),
        "can_edit": core.can(user, "classes.edit"),
        "mindbody_note": (
            "Public studio details are local Classy data. Mindbody class sync keeps using the stable studio ID/location mapping, "
            "so editing a public name, address, image or default capacity does not rename a Mindbody location."
        ),
    }


@app.patch("/api/staff/studios/{studio_id}")
def update_studio(
    studio_id: str,
    data: StudioUpdate,
    user: core.User = Depends(core.require("classes.edit")),
    db: Session = Depends(core.db_session),
):
    studio = db.get(core.Studio, studio_id)
    if not studio:
        raise HTTPException(404, "studio_not_found")

    name = data.name.strip()
    address = data.address.strip()
    studio.name = name
    studio.address = address
    studio.capacity = data.capacity

    profile = _profile(db, studio_id)
    if not profile:
        profile = StudioProfile(studio_id=studio_id)
        db.add(profile)

    profile.name_override = name
    profile.address_override = address
    profile.capacity_override = data.capacity
    profile.short_name = data.short_name.strip()
    profile.public_type = data.public_type.strip()
    profile.image_url = data.image_url.strip()
    profile.description = data.description.strip()
    profile.sort_order = data.sort_order
    db.commit()
    db.refresh(studio)
    return studio_dict(studio, db)
