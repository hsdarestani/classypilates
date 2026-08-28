from typing import Literal

from fastapi import BackgroundTasks, Depends, HTTPException
from sqlalchemy import ForeignKey, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

import feedback_app as feedback
import main as core

app = feedback.app


class ClassLanguage(core.Base):
    __tablename__ = "class_languages"
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), primary_key=True)
    language: Mapped[str] = mapped_column(String(8), default="de")


core.Base.metadata.create_all(core.engine)


# Keep the class language on the canonical class payload so the staff UI and
# public /api/schedule endpoint receive exactly the same value.
_base_class_dict = core.class_dict


def class_dict_with_language(c: core.ClassSession, db: Session):
    payload = _base_class_dict(c, db)
    row = db.get(ClassLanguage, c.id)
    payload["language"] = (row.language if row else "de").lower()
    return payload


core.class_dict = class_dict_with_language


class ClassInV3(feedback.ClassInV2):
    language: Literal["de", "en"] = "de"


def _save_language(db: Session, class_ids: list[int], language: str):
    lang = (language or "de").strip().lower()
    if lang not in {"de", "en"}:
        raise HTTPException(400, "invalid_class_language")
    for class_id in class_ids:
        row = db.get(ClassLanguage, class_id)
        if row:
            row.language = lang
        else:
            db.add(ClassLanguage(class_id=class_id, language=lang))
    db.commit()


def _base_input(data: ClassInV3):
    return feedback.ClassInV2(**data.model_dump(exclude={"language"}))


# feedback_app already owns the notification-aware class create/edit routes.
# Replace only those two routes and delegate the actual class work back to it,
# then persist the language metadata.
feedback._drop_route("/api/staff/classes", "POST")
feedback._drop_route("/api/staff/classes/{class_id}", "PATCH")


@app.post("/api/staff/classes")
def create_class_v3(
    data: ClassInV3,
    user: core.User = Depends(core.require("classes.create")),
    db: Session = Depends(core.db_session),
):
    base = _base_input(data)
    result = feedback.create_class_v2(base, user, db)

    repeat_months = min(36, max(1, int(base.repeat_months or 1)))
    if base.repeat_weeks is not None and base.repeat_months == 1:
        repeat_months = 1
    starts = [feedback._plus_months(base.starts_at, month) for month in range(repeat_months)]
    rows = db.scalars(
        select(core.ClassSession).where(
            core.ClassSession.studio_id == base.studio_id,
            core.ClassSession.title == base.title.strip(),
            core.ClassSession.starts_at.in_(starts),
            core.ClassSession.status == "active",
        )
    ).all()
    class_ids = [row.id for row in rows]
    if result.get("class", {}).get("id") and result["class"]["id"] not in class_ids:
        class_ids.append(result["class"]["id"])
    _save_language(db, class_ids, data.language)

    first = db.get(core.ClassSession, result["class"]["id"])
    if first:
        result["class"] = core.class_dict(first, db)
    result["language"] = data.language
    return result


@app.patch("/api/staff/classes/{class_id}")
def edit_class_v3(
    class_id: int,
    data: ClassInV3,
    background_tasks: BackgroundTasks,
    user: core.User = Depends(core.current_user),
    db: Session = Depends(core.db_session),
):
    base = _base_input(data)
    feedback.edit_class_v2(class_id, base, background_tasks, user, db)
    _save_language(db, [class_id], data.language)
    klass = db.get(core.ClassSession, class_id)
    if not klass:
        raise HTTPException(404, "not_found")
    return core.class_dict(klass, db)
