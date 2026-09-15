import hashlib
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import BackgroundTasks, HTTPException, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

import feedback_app as feedback
import main as core

app = feedback.app
RESET_TTL_MINUTES = 30
RESET_BASE_URL = os.getenv("PASSWORD_RESET_BASE_URL", "https://new.classypilates.de").rstrip("/")


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    password: str


def _password_fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:24]


def _reset_token(user: core.User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "purpose": "password_reset",
        "ph": _password_fingerprint(user.password_hash),
        "iat": now,
        "exp": now + timedelta(minutes=RESET_TTL_MINUTES),
    }
    return jwt.encode(payload, core.JWT_SECRET, algorithm="HS256")


def _decode_reset_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, core.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(400, "reset_token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(400, "reset_token_invalid") from exc
    if payload.get("purpose") != "password_reset" or not str(payload.get("sub") or "").isdigit():
        raise HTTPException(400, "reset_token_invalid")
    return payload


@app.post("/api/auth/password-reset/request")
def request_password_reset(
    data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db=core.Depends(core.db_session),
):
    # Always return the same response to avoid exposing whether an email exists.
    user = db.scalar(select(core.User).where(core.User.email == str(data.email).strip().lower()))
    if user and user.is_active:
        token = _reset_token(user)
        url = f"{RESET_BASE_URL}/reset-password.html?token={token}"
        background_tasks.add_task(
            core.send_transactional_email,
            user.email,
            "Reset your Classy Pilates password",
            "Reset your password",
            [
                f"Hello {user.first_name or 'Classy Client'},",
                "We received a request to reset the password for your Classy Pilates account.",
                f"Open this secure link within {RESET_TTL_MINUTES} minutes: {url}",
                "If you did not request this, you can ignore this email. Your current password remains unchanged.",
            ],
        )
    return {"ok": True}


@app.post("/api/auth/password-reset/confirm")
def confirm_password_reset(
    data: PasswordResetConfirm,
    response: Response,
    db=core.Depends(core.db_session),
):
    if len(data.password) < 10:
        raise HTTPException(400, "password_too_short")

    payload = _decode_reset_token(data.token)
    user = db.get(core.User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(400, "reset_token_invalid")
    if payload.get("ph") != _password_fingerprint(user.password_hash):
        # The password changed after this token was issued: token is one-time-use.
        raise HTTPException(400, "reset_token_used")

    user.password_hash = core.pwd.hash(data.password)
    db.commit()
    db.refresh(user)

    session_token = core.make_token(user)
    response.set_cookie(
        "cp_session",
        session_token,
        max_age=core.JWT_TTL_HOURS * 3600,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return {"ok": True, "user": core.user_dict(user)}
