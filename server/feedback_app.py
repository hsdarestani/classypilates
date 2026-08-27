import os
import smtplib
import ssl
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

import main as core

app = core.app
BERLIN = ZoneInfo("Europe/Berlin")
ALLOWED_PACKS = {1, 5, 10, 20, 30, 50}
KNOWN_PACK_PRICES = {1: 2800, 5: 11900, 10: 21900, 20: 39900}


class BookingPreference(core.Base):
    __tablename__ = "booking_preferences"
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), primary_key=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    sepa_account_holder: Mapped[str] = mapped_column(String(180), default="")
    sepa_iban_last4: Mapped[str] = mapped_column(String(4), default="")
    sepa_mandate_accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Membership(core.Base):
    __tablename__ = "memberships"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    credits_per_month: Mapped[int] = mapped_column(Integer)
    payment_method: Mapped[str] = mapped_column(String(30), default="sepa")
    status: Mapped[str] = mapped_column(String(30), default="active")
    provider_status: Mapped[str] = mapped_column(String(40), default="pending_provider")
    starts_on: Mapped[str] = mapped_column(String(20))
    next_charge_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ClassNotification(core.Base):
    __tablename__ = "class_notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), index=True)
    booking_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    recipient: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(40), default="queued")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


core.Base.metadata.create_all(core.engine)


class ClassInV2(BaseModel):
    studio_id: str
    title: str
    description: str = ""
    class_type: str = "Reformer"
    coach_id: Optional[int] = None
    starts_at: datetime
    duration: int = 50
    capacity: int = 10
    repeat_months: int = 1
    repeat_weeks: Optional[int] = None


class ClassPassSaleInV2(BaseModel):
    mode: str
    customer_id: Optional[int] = None
    payment_method: str = "cash"
    credits: int = 10
    amount_cents: Optional[int] = None


class PublicBookingInV2(BaseModel):
    classId: int | str
    email: EmailStr
    firstName: str = ""
    lastName: str = ""
    phone: str = ""
    spot: Optional[int] = None
    paymentMethod: str = ""
    studioId: str = ""
    title: str = ""
    classType: str = "Reformer"
    startsAt: datetime
    duration: int = 50
    capacity: int = 10
    coachName: str = ""
    language: str = "en"
    sepaAccountHolder: str = ""
    sepaIbanLast4: str = ""
    sepaMandateAccepted: bool = False


class MembershipIn(BaseModel):
    customer_id: int
    amount_cents: int
    credits_per_month: int
    starts_on: str
    payment_method: str = "sepa"


def _drop_route(path: str, method: str):
    method = method.upper()
    app.router.routes[:] = [
        route for route in app.router.routes
        if not (getattr(route, "path", None) == path and method in (getattr(route, "methods", set()) or set()))
    ]


for _path, _method in [
    ("/api/staff/classes", "POST"),
    ("/api/staff/classes/{class_id}", "PATCH"),
    ("/api/staff/classes/{class_id}", "DELETE"),
    ("/api/staff/class-passes/sell", "POST"),
    ("/api/bookings", "POST"),
]:
    _drop_route(_path, _method)


def _plus_months(value: datetime, months: int) -> datetime:
    year = value.year + (value.month - 1 + months) // 12
    month = (value.month - 1 + months) % 12 + 1
    month_lengths = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day = min(value.day, month_lengths[month - 1])
    return value.replace(year=year, month=month, day=day)


def _local_time(value: datetime) -> str:
    try:
        return core.as_utc(value).astimezone(BERLIN).strftime("%d.%m.%Y · %H:%M")
    except Exception:
        return str(value)


def _session_snapshot(c: core.ClassSession):
    return {
        "title": c.title,
        "type": c.class_type,
        "starts_at": c.starts_at,
        "studio": c.studio.name if c.studio else c.studio_id,
        "coach": c.coach.display_name if c.coach else "—",
        "duration": c.duration,
        "capacity": c.capacity,
    }


def _smtp_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _send_notification(notification_id: int, recipient: str, subject: str, body: str):
    host = os.getenv("SMTP_HOST", "").strip()
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASS", "")
    sender = os.getenv("SMTP_FROM", user or "info@classypilates.de").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    use_ssl = _smtp_bool("SMTP_SSL", False)
    use_starttls = _smtp_bool("SMTP_STARTTLS", not use_ssl)
    status, error = "sent", ""
    try:
        if not host:
            raise RuntimeError("SMTP_HOST is not configured")
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)
        if use_ssl:
            client = smtplib.SMTP_SSL(host, port, timeout=15, context=ssl.create_default_context())
        else:
            client = smtplib.SMTP(host, port, timeout=15)
        with client:
            client.ehlo()
            if use_starttls and not use_ssl:
                client.starttls(context=ssl.create_default_context())
                client.ehlo()
            if user:
                client.login(user, password)
            client.send_message(msg)
    except Exception as exc:
        status, error = "failed", str(exc)[:1500]
    with core.SessionLocal() as db:
        row = db.get(ClassNotification, notification_id)
        if row:
            row.status = status
            row.error = error
            row.sent_at = datetime.now(timezone.utc) if status == "sent" else None
            db.commit()


def _notification_copy(language: str, event_type: str, booking: core.Booking, before: dict, after: dict, changed: list[str], credit_returned: bool = False):
    de = language == "de"
    name = (booking.customer_name or "").strip()
    hello = f"Hallo {name}," if name and de else (f"Hi {name}," if name else ("Hallo," if de else "Hi,"))
    if event_type == "cancelled":
        subject = "Dein Classy Pilates Kurs wurde abgesagt" if de else "Your Classy Pilates class was cancelled"
        credit_line = (
            "Dein verwendeter Class Credit wurde deinem Konto sofort wieder gutgeschrieben."
            if credit_returned and de else
            "Your used Class Credit was returned to your account immediately."
            if credit_returned else
            "Falls eine Rückerstattung nötig ist, wird sie entsprechend der gewählten Zahlungsart bearbeitet."
            if de else
            "If a refund is needed, it will be handled according to your payment method."
        )
        body = (
            f"{hello}\n\n"
            + ("leider wurde dein gebuchter Kurs abgesagt.\n\n" if de else "Unfortunately, your booked class has been cancelled.\n\n")
            + f"{after['title']} · {after['type']}\n{_local_time(after['starts_at'])}\n{after['studio']}\n"
            + (("Trainer: " if de else "Coach: ") + after['coach'] + "\n\n")
            + credit_line
            + ("\n\nDein Classy Pilates Team" if de else "\n\nYour Classy Pilates team")
        )
        return subject, body
    trainer_only = changed and set(changed) == {"coach"}
    subject = (
        "Trainerwechsel bei deinem Classy Pilates Kurs" if trainer_only and de else
        "Coach change for your Classy Pilates class" if trainer_only else
        "Änderung zu deinem Classy Pilates Kurs" if de else
        "Update to your Classy Pilates class"
    )
    labels = {
        "title": ("Kurs", "Class"), "type": ("Typ", "Type"), "starts_at": ("Termin", "Time"),
        "studio": ("Studio", "Studio"), "coach": ("Trainer", "Coach"), "duration": ("Dauer", "Duration"),
        "capacity": ("Kapazität", "Capacity"),
    }
    change_lines = []
    for key in changed:
        old = _local_time(before[key]) if key == "starts_at" else before[key]
        new = _local_time(after[key]) if key == "starts_at" else after[key]
        label = labels.get(key, (key, key))[0 if de else 1]
        suffix = " Min." if key == "duration" else ""
        change_lines.append(f"{label}: {old}{suffix} → {new}{suffix}")
    body = (
        f"{hello}\n\n"
        + ("bei deinem gebuchten Kurs hat sich etwas geändert. Hier sind die Änderungen:\n\n" if de else "Something changed in your booked class. Here are the updates:\n\n")
        + "\n".join(change_lines)
        + "\n\n"
        + f"{after['title']} · {after['type']}\n{_local_time(after['starts_at'])}\n{after['studio']}\n"
        + (("Trainer: " if de else "Coach: ") + after['coach'])
        + ("\n\nDeine Buchung bleibt bestehen.\n\nDein Classy Pilates Team" if de else "\n\nYour booking remains active.\n\nYour Classy Pilates team")
    )
    return subject, body


def _queue_class_notifications(db: Session, c: core.ClassSession, event_type: str, before: dict, after: dict, changed: list[str], background: BackgroundTasks, refunded_booking_ids: set[int] | None = None):
    bookings = db.scalars(select(core.Booking).where(core.Booking.class_id == c.id, core.Booking.status.in_(["reserved", "cancelled"]))).all()
    queued = 0
    seen = set()
    for booking in bookings:
        email = (booking.email or "").strip().lower()
        if not email or email in seen:
            continue
        seen.add(email)
        pref = db.get(BookingPreference, booking.id)
        language = (pref.language if pref else "en").lower()
        subject, body = _notification_copy(language, event_type, booking, before, after, changed, booking.id in (refunded_booking_ids or set()))
        row = ClassNotification(class_id=c.id, booking_id=booking.id, event_type=event_type, recipient=email, subject=subject)
        db.add(row)
        db.flush()
        background.add_task(_send_notification, row.id, email, subject, body)
        queued += 1
    return queued


@app.post("/api/staff/classes")
def create_class_v2(data: ClassInV2, user: core.User = Depends(core.require("classes.create")), db: Session = Depends(core.db_session)):
    coach_id = data.coach_id
    if user.coach and not core.can(user, "classes.edit"):
        coach_id = user.coach.id
    studio = db.get(core.Studio, data.studio_id)
    if not studio:
        raise HTTPException(400, "invalid_studio")
    title = data.title.strip()
    if not 2 <= len(title) <= 180:
        raise HTTPException(400, "invalid_class_title")
    description = data.description.strip()[:2000]
    repeat_months = min(36, max(1, int(data.repeat_months or 1)))
    if data.repeat_weeks is not None and data.repeat_months == 1:
        repeat_months = 1
    created = []
    for month in range(repeat_months):
        starts_at = _plus_months(data.starts_at, month)
        duplicate = db.scalar(select(core.ClassSession.id).where(
            core.ClassSession.studio_id == data.studio_id,
            core.ClassSession.title == title,
            core.ClassSession.starts_at == starts_at,
            core.ClassSession.status == "active",
        ))
        if duplicate:
            continue
        c = core.ClassSession(
            studio_id=data.studio_id, title=title, description=description, class_type=data.class_type,
            coach_id=coach_id, starts_at=starts_at, duration=min(180, max(15, data.duration)),
            capacity=min(100, max(1, data.capacity)), created_by=user.id,
        )
        db.add(c)
        db.flush()
        created.append(c)
    if not created:
        raise HTTPException(409, "all_recurring_classes_exist")
    db.commit()
    return {"class": core.class_dict(created[0], db), "created_count": len(created), "requested_count": repeat_months, "recurrence": "monthly"}


@app.patch("/api/staff/classes/{class_id}")
def edit_class_v2(class_id: int, data: ClassInV2, background_tasks: BackgroundTasks, user: core.User = Depends(core.current_user), db: Session = Depends(core.db_session)):
    c = db.get(core.ClassSession, class_id)
    if not c:
        raise HTTPException(404, "not_found")
    if not core.can(user, "classes.edit"):
        if not (core.can(user, "classes.edit_own") and user.coach and c.coach_id == user.coach.id):
            raise HTTPException(403, "permission_denied")
    before = _session_snapshot(c)
    studio = db.get(core.Studio, data.studio_id)
    if not studio:
        raise HTTPException(400, "invalid_studio")
    title = data.title.strip()
    if not 2 <= len(title) <= 180:
        raise HTTPException(400, "invalid_class_title")
    c.studio_id = data.studio_id
    c.title = title
    c.description = data.description.strip()[:2000]
    c.class_type = data.class_type
    c.starts_at = data.starts_at
    c.duration = min(180, max(15, data.duration))
    c.capacity = min(100, max(1, data.capacity))
    c.studio = studio
    if core.can(user, "classes.edit"):
        c.coach_id = data.coach_id
        c.coach = db.get(core.Coach, data.coach_id) if data.coach_id else None
    db.flush()
    after = _session_snapshot(c)
    changed = [k for k in ("title", "type", "starts_at", "studio", "coach", "duration", "capacity") if before[k] != after[k]]
    queued = _queue_class_notifications(db, c, "updated", before, after, changed, background_tasks) if changed else 0
    db.commit()
    return {"class": core.class_dict(c, db), "notifications_queued": queued, "changed": changed}


@app.delete("/api/staff/classes/{class_id}")
def delete_class_v2(class_id: int, background_tasks: BackgroundTasks, user: core.User = Depends(core.require("classes.delete")), db: Session = Depends(core.db_session)):
    c = db.get(core.ClassSession, class_id)
    if not c:
        raise HTTPException(404, "not_found")
    before = _session_snapshot(c)
    c.status = "cancelled"
    refunded = set()
    bookings = db.scalars(select(core.Booking).where(core.Booking.class_id == c.id, core.Booking.status == "reserved")).all()
    for booking in bookings:
        booking.status = "cancelled"
        if booking.payment_method == "class_credit":
            link = db.scalar(select(core.CustomerBookingLink).where(core.CustomerBookingLink.booking_id == booking.id))
            if link:
                profile = db.get(core.CustomerProfile, link.user_id)
                if profile:
                    profile.credits += 1
                    refunded.add(booking.id)
    db.flush()
    after = _session_snapshot(c)
    queued = _queue_class_notifications(db, c, "cancelled", before, after, [], background_tasks, refunded)
    db.commit()
    return {"ok": True, "notifications_queued": queued, "credits_returned": len(refunded)}


@app.post("/api/staff/class-passes/sell")
def sell_class_pass_v2(data: ClassPassSaleInV2, user: core.User = Depends(core.require("customers.manage")), db: Session = Depends(core.db_session)):
    mode = data.mode.strip().lower()
    if mode not in {"account", "gift"}:
        raise HTTPException(400, "invalid_mode")
    credits = int(data.credits)
    if credits not in ALLOWED_PACKS:
        raise HTTPException(400, "invalid_pack_size")
    payment_method = data.payment_method.strip().lower() or "cash"
    amount_cents = int(data.amount_cents) if data.amount_cents is not None else KNOWN_PACK_PRICES.get(credits)
    if amount_cents is None or amount_cents < 0:
        raise HTTPException(400, "price_required_for_pack")
    now = datetime.now(timezone.utc)
    if mode == "account":
        if not data.customer_id:
            raise HTTPException(400, "customer_required")
        customer = db.get(core.User, data.customer_id)
        if not customer or core.portal_for(customer) != "/account":
            raise HTTPException(404, "customer_not_found")
        profile = db.scalar(select(core.CustomerProfile).where(core.CustomerProfile.user_id == customer.id).with_for_update())
        if not profile:
            profile = core.CustomerProfile(user_id=customer.id)
            db.add(profile)
            db.flush()
        profile.credits += credits
        sale = core.ClassPassSale(
            mode="account", credits=credits, amount_cents=amount_cents, payment_method=payment_method,
            customer_user_id=customer.id, redeemed_by_user_id=customer.id, created_by=user.id,
            status="assigned", redeemed_at=now,
        )
        db.add(sale)
        db.commit()
        db.refresh(sale)
        return {"sale": {"id": sale.id, "mode": sale.mode, "credits": credits, "amount_cents": amount_cents, "customer_id": customer.id, "balance": profile.credits, "status": sale.status}}
    code = "CLASSY-" + os.urandom(3).hex().upper() + "-" + os.urandom(3).hex().upper()
    while db.scalar(select(core.ClassPassSale.id).where(core.ClassPassSale.code == code)):
        code = "CLASSY-" + os.urandom(3).hex().upper() + "-" + os.urandom(3).hex().upper()
    sale = core.ClassPassSale(mode="gift", credits=credits, amount_cents=amount_cents, payment_method=payment_method, code=code, created_by=user.id, status="active")
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return {"sale": {"id": sale.id, "mode": sale.mode, "credits": credits, "amount_cents": amount_cents, "code": code, "status": sale.status}}


@app.post("/api/bookings")
def public_booking_v2(data: PublicBookingInV2, user: Optional[core.User] = Depends(core.optional_user), db: Session = Depends(core.db_session)):
    base = core.PublicBookingIn(
        classId=data.classId, email=data.email, firstName=data.firstName, lastName=data.lastName, phone=data.phone,
        spot=data.spot, paymentMethod=data.paymentMethod, studioId=data.studioId, title=data.title, classType=data.classType,
        startsAt=data.startsAt, duration=data.duration, capacity=data.capacity, coachName=data.coachName,
    )
    c = core.resolve_public_class(base, user, db)
    if not c or c.status != "active":
        raise HTTPException(409, "class_unavailable")
    if core.as_utc(c.starts_at) <= datetime.now(timezone.utc):
        raise HTTPException(409, "class_started")
    live_reserved = db.scalar(select(func.count(core.Booking.id)).where(core.Booking.class_id == c.id, core.Booking.status == "reserved")) or 0
    reserved = int(c.imported_bookings or 0) + int(live_reserved)
    if reserved >= c.capacity:
        raise HTTPException(409, "class_full")
    duplicate = db.scalar(select(core.Booking).where(core.Booking.class_id == c.id, core.Booking.email == data.email.lower(), core.Booking.status == "reserved"))
    if duplicate:
        raise HTTPException(409, "duplicate_booking")
    if data.spot:
        if data.spot <= int(c.imported_bookings or 0):
            raise HTTPException(409, "spot_taken")
        spot_taken = db.scalar(select(core.Booking).where(core.Booking.class_id == c.id, core.Booking.spot_number == data.spot, core.Booking.status == "reserved"))
        if spot_taken:
            raise HTTPException(409, "spot_taken")
    ref = "CP-" + os.urandom(4).hex().upper()
    use_credit = False
    profile = None
    if user and core.portal_for(user) == "/account" and user.email.lower() == data.email.lower():
        profile = db.scalar(select(core.CustomerProfile).where(core.CustomerProfile.user_id == user.id).with_for_update())
        if profile and profile.credits > 0:
            profile.credits -= 1
            use_credit = True
    booking = core.Booking(
        reference=ref, class_id=c.id, customer_name=(data.firstName + " " + data.lastName).strip(),
        email=data.email.lower(), phone=data.phone, spot_number=data.spot,
        payment_method="class_credit" if use_credit else data.paymentMethod,
        payment_status="paid" if use_credit else "pending", amount_cents=0 if use_credit else (2800 if data.paymentMethod else 0),
    )
    db.add(booking)
    db.flush()
    if user and core.portal_for(user) == "/account" and user.email.lower() == data.email.lower():
        db.add(core.CustomerBookingLink(booking_id=booking.id, user_id=user.id))
    language = data.language.strip().lower()
    if language not in {"de", "en"}:
        language = "en"
    db.add(BookingPreference(
        booking_id=booking.id,
        language=language,
        sepa_account_holder=data.sepaAccountHolder.strip()[:180] if data.sepaMandateAccepted else "",
        sepa_iban_last4=data.sepaIbanLast4.strip()[-4:] if data.sepaMandateAccepted else "",
        sepa_mandate_accepted_at=datetime.now(timezone.utc) if data.sepaMandateAccepted else None,
    ))
    db.commit()
    return {"booking": {"reference": ref}, "payment_status": booking.payment_status, "credit_used": use_credit, "credits_remaining": profile.credits if profile else None, "language": language}


@app.get("/api/staff/booking-preferences")
def staff_booking_preferences(user: core.User = Depends(core.require("bookings.view")), db: Session = Depends(core.db_session)):
    rows = db.execute(
        select(core.Booking.reference, BookingPreference.language, BookingPreference.sepa_iban_last4, BookingPreference.sepa_mandate_accepted_at)
        .join(BookingPreference, BookingPreference.booking_id == core.Booking.id)
        .order_by(core.Booking.created_at.desc())
        .limit(500)
    ).all()
    return {"preferences": [
        {"reference": ref, "language": language, "sepa": bool(last4), "iban_last4": last4 or "", "mandate_at": mandate.isoformat() if mandate else None}
        for ref, language, last4, mandate in rows
    ]}


@app.get("/api/staff/class-notifications")
def staff_class_notifications(user: core.User = Depends(core.require("classes.view")), db: Session = Depends(core.db_session)):
    rows = db.scalars(select(ClassNotification).order_by(ClassNotification.created_at.desc()).limit(100)).all()
    return {"notifications": [
        {"id": x.id, "class_id": x.class_id, "event_type": x.event_type, "recipient": x.recipient, "subject": x.subject, "status": x.status, "error": x.error, "created_at": x.created_at.isoformat(), "sent_at": x.sent_at.isoformat() if x.sent_at else None}
        for x in rows
    ]}


@app.get("/api/staff/memberships")
def staff_memberships(user: core.User = Depends(core.require("customers.view")), db: Session = Depends(core.db_session)):
    rows = db.scalars(select(Membership).order_by(Membership.created_at.desc()).limit(200)).all()
    result = []
    for row in rows:
        customer = db.get(core.User, row.customer_user_id)
        result.append({
            "id": row.id, "customer_id": row.customer_user_id,
            "customer": ((customer.first_name + " " + customer.last_name).strip() or customer.email) if customer else str(row.customer_user_id),
            "email": customer.email if customer else "", "amount_cents": row.amount_cents,
            "credits_per_month": row.credits_per_month, "payment_method": row.payment_method,
            "status": row.status, "provider_status": row.provider_status, "starts_on": row.starts_on,
            "next_charge_at": row.next_charge_at.isoformat() if row.next_charge_at else None,
        })
    return {"memberships": result, "automatic_debit_ready": bool(os.getenv("STRIPE_SECRET_KEY") or os.getenv("SEPA_PROVIDER_KEY"))}


@app.post("/api/staff/memberships")
def create_membership(data: MembershipIn, user: core.User = Depends(core.require("customers.manage")), db: Session = Depends(core.db_session)):
    customer = db.get(core.User, data.customer_id)
    if not customer or core.portal_for(customer) != "/account":
        raise HTTPException(404, "customer_not_found")
    if data.amount_cents <= 0 or data.credits_per_month <= 0:
        raise HTTPException(400, "invalid_membership")
    try:
        start = date.fromisoformat(data.starts_on)
    except Exception:
        raise HTTPException(400, "invalid_start_date")
    next_charge = datetime.combine(start, datetime.min.time(), tzinfo=BERLIN).astimezone(timezone.utc)
    provider_ready = bool(os.getenv("STRIPE_SECRET_KEY") or os.getenv("SEPA_PROVIDER_KEY"))
    membership = Membership(
        customer_user_id=customer.id, amount_cents=data.amount_cents, credits_per_month=data.credits_per_month,
        payment_method=data.payment_method, status="active", provider_status="ready" if provider_ready else "pending_provider",
        starts_on=data.starts_on, next_charge_at=next_charge, created_by=user.id,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return {"membership": {"id": membership.id, "status": membership.status, "provider_status": membership.provider_status}}
