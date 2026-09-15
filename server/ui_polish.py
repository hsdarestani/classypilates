import os
import re

from fastapi import Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import feedback_app as feedback
import main as core

app = feedback.app


# The marketing/schedule UI already has curated coach portraits in /public.
# Imported Mindbody coach rows do not necessarily carry a photo_url, so expose
# the same curated portraits through the canonical coach payload as a fallback.
_COACH_PHOTOS = (
    (re.compile(r"^anna\s+k\b", re.I), "/anna%20K.jpg"),
    (re.compile(r"^anna$", re.I), "/anna.jpg"),
    (re.compile(r"^ouafaa\b", re.I), "/Ouafaa.jpeg"),
    (re.compile(r"^arja\b", re.I), "/Arja.jpeg"),
    (re.compile(r"^sophie\b", re.I), "/Sophie.jpg"),
    (re.compile(r"^schahrzad\b", re.I), "/Schahrzad.jpg"),
    (re.compile(r"^sani\b", re.I), "/Sani.jpg"),
    (re.compile(r"^sayna\b", re.I), "/sayna.jpg"),
    (re.compile(r"^luca\b", re.I), "/luca.jpg"),
    (re.compile(r"^zora\b", re.I), "/zora.jpg"),
)


def _fallback_coach_photo(display_name: str) -> str:
    normalized = re.sub(r"\s+", " ", (display_name or "").replace(".", " ").strip())
    for pattern, url in _COACH_PHOTOS:
        if pattern.search(normalized):
            return url
    return ""


_original_coach_dict = core.coach_dict


def coach_dict_with_curated_photo(coach: core.Coach):
    payload = _original_coach_dict(coach)
    if not payload.get("photo_url"):
        payload["photo_url"] = _fallback_coach_photo(coach.display_name)
    return payload


core.coach_dict = coach_dict_with_curated_photo

# Keep /api/auth/me consistent for coach accounts as well.
_original_user_dict = getattr(core, "user_dict", None)
if _original_user_dict:
    def user_dict_with_curated_photo(user: core.User):
        payload = _original_user_dict(user)
        coach = payload.get("coach") if isinstance(payload, dict) else None
        if coach and not coach.get("photo_url") and user.coach:
            coach["photo_url"] = _fallback_coach_photo(user.coach.display_name)
        return payload

    core.user_dict = user_dict_with_curated_photo


def _online_credit_orders_total(db: Session, status: str) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.sum(core.PaymentOrder.amount_cents), 0)).where(
                core.PaymentOrder.booking_reference.is_(None),
                core.PaymentOrder.status == status,
            )
        )
        or 0
    )


def _sumup_count(db: Session, status: str) -> int:
    return int(
        db.scalar(
            select(func.count(core.PaymentOrder.id)).where(
                core.PaymentOrder.provider == "sumup",
                core.PaymentOrder.status == status,
            )
        )
        or 0
    )


@app.get("/api/staff/dashboard")
def polished_dashboard(
    user: core.User = Depends(core.require("dashboard.view")),
    db: Session = Depends(core.db_session),
):
    now = core.datetime.now(core.timezone.utc)
    class_count = db.scalar(
        select(func.count(core.ClassSession.id)).where(
            core.ClassSession.starts_at >= now,
            core.ClassSession.status == "active",
        )
    ) or 0
    live_booking_count = db.scalar(
        select(func.count(core.Booking.id)).where(core.Booking.status == "reserved")
    ) or 0
    imported_booking_count = db.scalar(
        select(func.coalesce(func.sum(core.ClassSession.imported_bookings), 0)).where(
            core.ClassSession.starts_at >= now,
            core.ClassSession.status == "active",
        )
    ) or 0
    coach_count = db.scalar(
        select(func.count(core.Coach.id)).where(core.Coach.active.is_(True))
    ) or 0
    paid_bookings = int(
        db.scalar(
            select(func.coalesce(func.sum(core.Booking.amount_cents), 0)).where(
                core.Booking.payment_status == "paid"
            )
        )
        or 0
    )
    on_site_passes = int(db.scalar(select(func.coalesce(func.sum(core.ClassPassSale.amount_cents), 0))) or 0)
    online_credit_orders = _online_credit_orders_total(db, "paid")
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_bookings = db.scalar(
        select(func.count(core.Booking.id)).where(core.Booking.created_at >= today)
    ) or 0
    return {
        "upcoming_classes": int(class_count),
        "active_bookings": int(live_booking_count) + int(imported_booking_count),
        "imported_bookings": int(imported_booking_count),
        "live_bookings": int(live_booking_count),
        "coaches": int(coach_count),
        "revenue_cents": paid_bookings + on_site_passes + online_credit_orders,
        "today_bookings": int(today_bookings),
    }


@app.get("/api/staff/finance")
def polished_finance(
    user: core.User = Depends(core.require("finance.view")),
    db: Session = Depends(core.db_session),
):
    booking_total = int(
        db.scalar(
            select(func.coalesce(func.sum(core.Booking.amount_cents), 0)).where(
                core.Booking.payment_status == "paid"
            )
        )
        or 0
    )
    pass_total = int(db.scalar(select(func.coalesce(func.sum(core.ClassPassSale.amount_cents), 0))) or 0)
    online_paid = _online_credit_orders_total(db, "paid")
    booking_pending = int(
        db.scalar(
            select(func.coalesce(func.sum(core.Booking.amount_cents), 0)).where(
                core.Booking.payment_status == "pending"
            )
        )
        or 0
    )
    online_pending = _online_credit_orders_total(db, "pending")

    paid_bookings = int(
        db.scalar(
            select(func.count(core.Booking.id)).where(core.Booking.payment_status == "paid")
        )
        or 0
    )
    paid_passes = int(db.scalar(select(func.count(core.ClassPassSale.id))) or 0)
    paid_online_orders = int(
        db.scalar(
            select(func.count(core.PaymentOrder.id)).where(
                core.PaymentOrder.booking_reference.is_(None),
                core.PaymentOrder.status == "paid",
            )
        )
        or 0
    )

    recent_bookings = db.scalars(
        select(core.Booking).order_by(core.Booking.created_at.desc()).limit(40)
    ).all()
    recent_passes = db.scalars(
        select(core.ClassPassSale).order_by(core.ClassPassSale.created_at.desc()).limit(30)
    ).all()
    recent_online = db.scalars(
        select(core.PaymentOrder)
        .where(core.PaymentOrder.booking_reference.is_(None))
        .order_by(core.PaymentOrder.created_at.desc())
        .limit(40)
    ).all()

    rows = [
        {
            "reference": booking.reference,
            "email": booking.email,
            "amount_cents": booking.amount_cents,
            "payment_status": booking.payment_status,
            "payment_method": booking.payment_method or "—",
            "provider": "sumup" if booking.payment_method == "sumup" else booking.payment_method or "—",
            "kind": "class_booking",
            "created_at": booking.created_at.isoformat(),
        }
        for booking in recent_bookings
    ]
    for sale in recent_passes:
        customer = db.get(core.User, sale.customer_user_id) if sale.customer_user_id else None
        rows.append(
            {
                "reference": sale.code or f"PASS-{sale.id:06d}",
                "email": customer.email if customer else "Gift sale",
                "amount_cents": sale.amount_cents,
                "payment_status": "paid",
                "payment_method": f"on-site {sale.payment_method}",
                "provider": "on_site",
                "kind": "class_credits",
                "created_at": sale.created_at.isoformat(),
            }
        )
    for order in recent_online:
        rows.append(
            {
                "reference": order.reference,
                "email": order.email,
                "amount_cents": order.amount_cents,
                "payment_status": order.status,
                "payment_method": "sumup",
                "provider": order.provider or "sumup",
                "kind": "class_credits",
                "created_at": order.created_at.isoformat(),
            }
        )
    rows.sort(key=lambda row: row["created_at"], reverse=True)

    sumup_configured = bool(os.getenv("SUMUPAPIKEY", "").strip() and os.getenv("SUMUPMERCHANT", "").strip())
    return {
        "revenue_cents": booking_total + pass_total + online_paid,
        "pending_cents": booking_pending + online_pending,
        "paid_bookings": paid_bookings + paid_passes + paid_online_orders,
        "rows": rows[:60],
        "provider": "sumup",
        "sumup_configured": sumup_configured,
        "sumup_paid_orders": _sumup_count(db, "paid"),
        "sumup_pending_orders": _sumup_count(db, "pending"),
        "sumup_paid_cents": int(
            db.scalar(
                select(func.coalesce(func.sum(core.PaymentOrder.amount_cents), 0)).where(
                    core.PaymentOrder.provider == "sumup",
                    core.PaymentOrder.status == "paid",
                )
            )
            or 0
        ),
        "sumup_pending_cents": int(
            db.scalar(
                select(func.coalesce(func.sum(core.PaymentOrder.amount_cents), 0)).where(
                    core.PaymentOrder.provider == "sumup",
                    core.PaymentOrder.status == "pending",
                )
            )
            or 0
        ),
    }


@app.get("/api/customer/payments")
def customer_payments(
    user: core.User = Depends(core.current_user),
    db: Session = Depends(core.db_session),
):
    if core.portal_for(user) != "/account":
        raise HTTPException(403, "customer_only")
    rows = db.scalars(
        select(core.PaymentOrder)
        .where(func.lower(core.PaymentOrder.email) == user.email.lower())
        .order_by(core.PaymentOrder.created_at.desc())
        .limit(100)
    ).all()
    return {
        "provider": "sumup",
        "payments": [
            {
                "reference": row.reference,
                "amount_cents": row.amount_cents,
                "credits": row.credits,
                "booking_reference": row.booking_reference,
                "status": row.status,
                "provider": row.provider or "sumup",
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
    }
