import csv
import io
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import jwt
from dateutil import parser as date_parser
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from openpyxl import load_workbook
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/classy.db")
JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_TTL_HOURS = int(os.getenv("JWT_TTL_HOURS", "24"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/data/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    permissions_json: Mapped[str] = mapped_column(Text, default="[]")
    system: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def permissions(self):
        try:
            return json.loads(self.permissions_json or "[]")
        except Exception:
            return []

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(120), default="")
    last_name: Mapped[str] = mapped_column(String(120), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    roles: Mapped[list[Role]] = relationship(secondary="user_roles", lazy="selectin")
    coach: Mapped[Optional["Coach"]] = relationship(back_populates="user", uselist=False)

class Studio(Base):
    __tablename__ = "studios"
    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    address: Mapped[str] = mapped_column(String(255), default="")
    capacity: Mapped[int] = mapped_column(Integer, default=10)

class Coach(Base):
    __tablename__ = "coaches"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String(160))
    photo_url: Mapped[str] = mapped_column(String(500), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    user: Mapped[Optional[User]] = relationship(back_populates="coach")

class ClassSession(Base):
    __tablename__ = "classes"
    id: Mapped[int] = mapped_column(primary_key=True)
    studio_id: Mapped[str] = mapped_column(ForeignKey("studios.id"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    class_type: Mapped[str] = mapped_column(String(80), default="Reformer")
    coach_id: Mapped[Optional[int]] = mapped_column(ForeignKey("coaches.id", ondelete="SET NULL"), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration: Mapped[int] = mapped_column(Integer, default=50)
    capacity: Mapped[int] = mapped_column(Integer, default=10)
    status: Mapped[str] = mapped_column(String(30), default="active")
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    coach: Mapped[Optional[Coach]] = relationship()
    studio: Mapped[Studio] = relationship()

class Booking(Base):
    __tablename__ = "bookings"
    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), index=True)
    customer_name: Mapped[str] = mapped_column(String(180), default="")
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str] = mapped_column(String(80), default="")
    spot_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="reserved")
    payment_status: Mapped[str] = mapped_column(String(30), default="pending")
    payment_method: Mapped[str] = mapped_column(String(60), default="")
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    klass: Mapped[ClassSession] = relationship()

class Waitlist(Base):
    __tablename__ = "waitlist"
    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    klass: Mapped[ClassSession] = relationship()

class ScheduleUpload(Base):
    __tablename__ = "schedule_uploads"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    saved_path: Mapped[str] = mapped_column(String(500))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(60), default="received")
    imported_rows: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(engine)

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

ALL_PERMISSIONS = [
    "dashboard.view", "finance.view", "bookings.view", "bookings.manage",
    "classes.view", "classes.create", "classes.edit", "classes.delete", "classes.edit_own",
    "coaches.view", "coaches.manage", "roles.manage", "users.manage", "schedules.upload",
    "marketing.view"
]
DEFAULT_COACH_PERMS = ["dashboard.view", "bookings.view", "classes.view", "classes.create", "classes.edit_own", "schedules.upload"]

STUDIOS = [
    ("bhf1", "Bahnhofsviertel · 1. OG", "Kaiserstraße 61 · 60329 Frankfurt", 8),
    ("ladies", "Bahnhofsviertel · Ladies 2. OG", "Kaiserstraße 61 · 60329 Frankfurt", 10),
    ("sachsen", "Sachsenhausen", "Zum Gipfelhof 5 · 60594 Frankfurt", 12),
    ("bornheim", "Bornheim", "Wiesenstraße 33 · 60385 Frankfurt", 8),
    ("mid", "Mid", "Große Eschenheimer Straße 45 · 60313 Frankfurt", 10),
    ("oval", "Oval", "Baseler Straße 10 · 60329 Frankfurt", 10),
]

def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def seed():
    with SessionLocal() as db:
        if not db.scalar(select(Role).where(Role.name == "Administrator")):
            db.add(Role(name="Administrator", description="Voller Zugriff", permissions_json=json.dumps(["*"]), system=True))
        if not db.scalar(select(Role).where(Role.name == "Coach")):
            db.add(Role(name="Coach", description="Standardzugriff für Coaches", permissions_json=json.dumps(DEFAULT_COACH_PERMS), system=True))
        for sid, name, address, cap in STUDIOS:
            if not db.get(Studio, sid):
                db.add(Studio(id=sid, name=name, address=address, capacity=cap))
        db.commit()
seed()

def user_permissions(user: User):
    perms = set()
    for role in user.roles:
        perms.update(role.permissions)
    return perms

def can(user: User, permission: str):
    perms = user_permissions(user)
    return "*" in perms or permission in perms

def make_token(user: User):
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user.id), "iat": int(now.timestamp()), "exp": int((now + timedelta(hours=JWT_TTL_HOURS)).timestamp())}, JWT_SECRET, algorithm="HS256")

def current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(db_session)):
    if not credentials:
        raise HTTPException(401, "login_required")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        user = db.get(User, int(payload["sub"]))
    except Exception:
        raise HTTPException(401, "invalid_token")
    if not user or not user.is_active:
        raise HTTPException(401, "inactive_user")
    return user

def require(permission: str):
    def dep(user: User = Depends(current_user)):
        if not can(user, permission):
            raise HTTPException(403, "permission_denied")
        return user
    return dep

def user_dict(user: User):
    return {
        "id": user.id, "email": user.email, "first_name": user.first_name, "last_name": user.last_name,
        "is_active": user.is_active,
        "roles": [{"id": r.id, "name": r.name, "permissions": r.permissions} for r in user.roles],
        "permissions": sorted(user_permissions(user)),
        "coach": None if not user.coach else {"id": user.coach.id, "display_name": user.coach.display_name, "photo_url": user.coach.photo_url}
    }

def class_dict(c: ClassSession, db: Session):
    reserved = db.scalar(select(func.count(Booking.id)).where(Booking.class_id == c.id, Booking.status == "reserved")) or 0
    return {
        "id": c.id, "studio": c.studio_id, "studio_name": c.studio.name if c.studio else c.studio_id,
        "name": c.title, "type": c.class_type, "coach": c.coach.display_name if c.coach else "Classy Coach",
        "coach_id": c.coach_id, "starts_at": c.starts_at.isoformat(), "duration": c.duration,
        "capacity": c.capacity, "reserved": reserved, "spots": max(0, c.capacity - reserved), "status": c.status
    }

app = FastAPI(title="Classy Pilates Production API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["https://classy.smarbiz.sbs", "http://localhost", "http://127.0.0.1"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class BootstrapIn(BaseModel):
    email: EmailStr
    password: str
    first_name: str = "Admin"
    last_name: str = ""

class RoleIn(BaseModel):
    name: str
    description: str = ""
    permissions: list[str] = []

class StaffIn(BaseModel):
    email: EmailStr
    password: str
    first_name: str = ""
    last_name: str = ""
    role_ids: list[int] = []
    coach_name: str = ""
    coach_photo: str = ""

class StaffUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[list[int]] = None

class ClassIn(BaseModel):
    studio_id: str
    title: str
    class_type: str = "Reformer"
    coach_id: Optional[int] = None
    starts_at: datetime
    duration: int = 50
    capacity: int = 10

class BookingUpdate(BaseModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None
    amount_cents: Optional[int] = None

class PublicBookingIn(BaseModel):
    classId: int
    email: EmailStr
    firstName: str = ""
    lastName: str = ""
    phone: str = ""
    spot: Optional[int] = None
    paymentMethod: str = ""

class WaitlistIn(BaseModel):
    classId: int
    email: EmailStr

@app.get("/api/health")
def health():
    return {"ok": True, "service": "classy-production"}

@app.get("/api/auth/status")
def auth_status(db: Session = Depends(db_session)):
    return {"configured": (db.scalar(select(func.count(User.id))) or 0) > 0}

@app.post("/api/auth/bootstrap")
def bootstrap(data: BootstrapIn, db: Session = Depends(db_session)):
    if (db.scalar(select(func.count(User.id))) or 0) > 0:
        raise HTTPException(409, "already_configured")
    if len(data.password) < 10:
        raise HTTPException(400, "password_too_short")
    role = db.scalar(select(Role).where(Role.name == "Administrator"))
    user = User(email=data.email.lower(), password_hash=pwd.hash(data.password), first_name=data.first_name, last_name=data.last_name, roles=[role])
    db.add(user); db.commit(); db.refresh(user)
    return {"token": make_token(user), "user": user_dict(user)}

@app.post("/api/auth/login")
def login(data: LoginIn, db: Session = Depends(db_session)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not pwd.verify(data.password, user.password_hash):
        raise HTTPException(401, "invalid_credentials")
    return {"token": make_token(user), "user": user_dict(user)}

@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return user_dict(user)

@app.get("/api/staff/dashboard")
def dashboard(user: User = Depends(require("dashboard.view")), db: Session = Depends(db_session)):
    now = datetime.now(timezone.utc)
    class_count = db.scalar(select(func.count(ClassSession.id)).where(ClassSession.starts_at >= now, ClassSession.status == "active")) or 0
    booking_count = db.scalar(select(func.count(Booking.id)).where(Booking.status == "reserved")) or 0
    coach_count = db.scalar(select(func.count(Coach.id)).where(Coach.active == True)) or 0
    paid_cents = db.scalar(select(func.coalesce(func.sum(Booking.amount_cents), 0)).where(Booking.payment_status == "paid")) or 0
    today_bookings = db.scalar(select(func.count(Booking.id)).where(Booking.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0))) or 0
    return {"upcoming_classes": class_count, "active_bookings": booking_count, "coaches": coach_count, "revenue_cents": int(paid_cents), "today_bookings": today_bookings}

@app.get("/api/staff/finance")
def finance(user: User = Depends(require("finance.view")), db: Session = Depends(db_session)):
    total = int(db.scalar(select(func.coalesce(func.sum(Booking.amount_cents), 0)).where(Booking.payment_status == "paid")) or 0)
    pending = int(db.scalar(select(func.coalesce(func.sum(Booking.amount_cents), 0)).where(Booking.payment_status == "pending")) or 0)
    paid_bookings = db.scalar(select(func.count(Booking.id)).where(Booking.payment_status == "paid")) or 0
    recent = db.scalars(select(Booking).order_by(Booking.created_at.desc()).limit(30)).all()
    return {"revenue_cents": total, "pending_cents": pending, "paid_bookings": paid_bookings, "rows": [{"reference": b.reference, "email": b.email, "amount_cents": b.amount_cents, "payment_status": b.payment_status, "payment_method": b.payment_method, "created_at": b.created_at.isoformat()} for b in recent]}

@app.get("/api/staff/roles")
def list_roles(user: User = Depends(current_user), db: Session = Depends(db_session)):
    if not (can(user, "roles.manage") or can(user, "users.manage")):
        raise HTTPException(403, "permission_denied")
    roles = db.scalars(select(Role).order_by(Role.name)).all()
    return {"permissions": ALL_PERMISSIONS, "roles": [{"id": r.id, "name": r.name, "description": r.description, "permissions": r.permissions, "system": r.system} for r in roles]}

@app.post("/api/staff/roles")
def create_role(data: RoleIn, user: User = Depends(require("roles.manage")), db: Session = Depends(db_session)):
    perms = [p for p in data.permissions if p in ALL_PERMISSIONS]
    role = Role(name=data.name.strip(), description=data.description, permissions_json=json.dumps(perms), system=False)
    db.add(role)
    try: db.commit()
    except Exception: db.rollback(); raise HTTPException(409, "role_exists")
    db.refresh(role)
    return {"id": role.id}

@app.patch("/api/staff/roles/{role_id}")
def update_role(role_id: int, data: RoleIn, user: User = Depends(require("roles.manage")), db: Session = Depends(db_session)):
    role = db.get(Role, role_id)
    if not role: raise HTTPException(404, "not_found")
    role.name = data.name.strip(); role.description = data.description
    if not role.system: role.permissions_json = json.dumps([p for p in data.permissions if p in ALL_PERMISSIONS])
    elif role.name == "Administrator": role.permissions_json = json.dumps(["*"])
    db.commit(); return {"ok": True}

@app.delete("/api/staff/roles/{role_id}")
def delete_role(role_id: int, user: User = Depends(require("roles.manage")), db: Session = Depends(db_session)):
    role = db.get(Role, role_id)
    if not role: raise HTTPException(404, "not_found")
    if role.system: raise HTTPException(400, "system_role")
    db.delete(role); db.commit(); return {"ok": True}

@app.get("/api/staff/users")
def list_users(user: User = Depends(require("users.manage")), db: Session = Depends(db_session)):
    return {"users": [user_dict(u) for u in db.scalars(select(User).order_by(User.created_at.desc())).all()]}

@app.post("/api/staff/users")
def create_staff(data: StaffIn, user: User = Depends(require("users.manage")), db: Session = Depends(db_session)):
    if len(data.password) < 8: raise HTTPException(400, "password_too_short")
    roles = db.scalars(select(Role).where(Role.id.in_(data.role_ids))).all() if data.role_ids else []
    u = User(email=data.email.lower(), password_hash=pwd.hash(data.password), first_name=data.first_name, last_name=data.last_name, roles=list(roles))
    db.add(u)
    try: db.flush()
    except Exception: db.rollback(); raise HTTPException(409, "email_exists")
    if data.coach_name:
        db.add(Coach(user_id=u.id, display_name=data.coach_name, photo_url=data.coach_photo))
    db.commit(); db.refresh(u)
    return user_dict(u)

@app.patch("/api/staff/users/{user_id}")
def update_staff(user_id: int, data: StaffUpdate, user: User = Depends(require("users.manage")), db: Session = Depends(db_session)):
    target = db.get(User, user_id)
    if not target: raise HTTPException(404, "not_found")
    if data.first_name is not None: target.first_name = data.first_name
    if data.last_name is not None: target.last_name = data.last_name
    if data.is_active is not None: target.is_active = data.is_active
    if data.role_ids is not None: target.roles = list(db.scalars(select(Role).where(Role.id.in_(data.role_ids))).all())
    db.commit(); return user_dict(target)

@app.get("/api/staff/coaches")
def list_coaches(user: User = Depends(require("coaches.view")), db: Session = Depends(db_session)):
    coaches = db.scalars(select(Coach).order_by(Coach.display_name)).all()
    return {"coaches": [{"id": c.id, "display_name": c.display_name, "photo_url": c.photo_url, "bio": c.bio, "active": c.active, "email": c.user.email if c.user else ""} for c in coaches]}

@app.get("/api/staff/classes")
def staff_classes(user: User = Depends(require("classes.view")), db: Session = Depends(db_session)):
    q = select(ClassSession).order_by(ClassSession.starts_at.desc()).limit(300)
    rows = db.scalars(q).all()
    if user.coach and not can(user, "classes.edit"):
        rows = [r for r in rows if r.coach_id == user.coach.id]
    return {"classes": [class_dict(c, db) for c in rows]}

@app.post("/api/staff/classes")
def create_class(data: ClassIn, user: User = Depends(require("classes.create")), db: Session = Depends(db_session)):
    coach_id = data.coach_id
    if user.coach and not can(user, "classes.edit"):
        coach_id = user.coach.id
    studio = db.get(Studio, data.studio_id)
    if not studio: raise HTTPException(400, "invalid_studio")
    c = ClassSession(studio_id=data.studio_id, title=data.title, class_type=data.class_type, coach_id=coach_id, starts_at=data.starts_at, duration=max(15, data.duration), capacity=max(1, data.capacity), created_by=user.id)
    db.add(c); db.commit(); db.refresh(c)
    return class_dict(c, db)

@app.patch("/api/staff/classes/{class_id}")
def edit_class(class_id: int, data: ClassIn, user: User = Depends(current_user), db: Session = Depends(db_session)):
    c = db.get(ClassSession, class_id)
    if not c: raise HTTPException(404, "not_found")
    if not can(user, "classes.edit"):
        if not (can(user, "classes.edit_own") and user.coach and c.coach_id == user.coach.id): raise HTTPException(403, "permission_denied")
    c.studio_id=data.studio_id; c.title=data.title; c.class_type=data.class_type; c.starts_at=data.starts_at; c.duration=data.duration; c.capacity=data.capacity
    if can(user, "classes.edit"): c.coach_id=data.coach_id
    db.commit(); return class_dict(c, db)

@app.delete("/api/staff/classes/{class_id}")
def delete_class(class_id: int, user: User = Depends(require("classes.delete")), db: Session = Depends(db_session)):
    c=db.get(ClassSession,class_id)
    if not c: raise HTTPException(404,"not_found")
    c.status="cancelled"; db.commit(); return {"ok":True}

@app.get("/api/staff/bookings")
def staff_bookings(user: User = Depends(require("bookings.view")), db: Session = Depends(db_session)):
    rows = db.scalars(select(Booking).order_by(Booking.created_at.desc()).limit(500)).all()
    if user.coach and not can(user, "bookings.manage"):
        rows = [b for b in rows if b.klass.coach_id == user.coach.id]
    return {"bookings": [{"id":b.id,"reference":b.reference,"class_id":b.class_id,"class_name":b.klass.title,"starts_at":b.klass.starts_at.isoformat(),"studio":b.klass.studio.name,"customer_name":b.customer_name,"email":b.email,"phone":b.phone,"spot_number":b.spot_number,"status":b.status,"payment_status":b.payment_status,"payment_method":b.payment_method,"amount_cents":b.amount_cents} for b in rows]}

@app.patch("/api/staff/bookings/{booking_id}")
def staff_booking_update(booking_id: int, data: BookingUpdate, user: User = Depends(require("bookings.manage")), db: Session = Depends(db_session)):
    b=db.get(Booking,booking_id)
    if not b: raise HTTPException(404,"not_found")
    if data.status is not None: b.status=data.status
    if data.payment_status is not None: b.payment_status=data.payment_status
    if data.amount_cents is not None: b.amount_cents=max(0,data.amount_cents)
    db.commit(); return {"ok":True}

def parse_upload_rows(content: bytes, filename: str):
    ext = Path(filename).suffix.lower()
    if ext == ".csv":
        text = content.decode("utf-8-sig", errors="replace")
        return list(csv.DictReader(io.StringIO(text)))
    if ext in (".xlsx", ".xlsm"):
        wb=load_workbook(io.BytesIO(content), read_only=True, data_only=True); ws=wb.active
        rows=list(ws.iter_rows(values_only=True));
        if not rows: return []
        headers=[str(x or "").strip() for x in rows[0]]
        return [{headers[i]: row[i] for i in range(min(len(headers),len(row)))} for row in rows[1:] if any(v is not None for v in row)]
    return []

def pick(row, *names):
    normalized={str(k).strip().lower():v for k,v in row.items()}
    for n in names:
        if n.lower() in normalized and normalized[n.lower()] not in (None,""): return normalized[n.lower()]
    return None

def studio_from_value(value, db):
    s=str(value or "").lower()
    for sid,name,_,_ in STUDIOS:
        if sid in s or name.lower().split(" · ")[0] in s: return sid
    return None

@app.get("/api/staff/uploads")
def list_uploads(user: User = Depends(require("schedules.upload")), db: Session = Depends(db_session)):
    rows=db.scalars(select(ScheduleUpload).order_by(ScheduleUpload.created_at.desc()).limit(100)).all()
    return {"uploads":[{"id":x.id,"filename":x.filename,"status":x.status,"imported_rows":x.imported_rows,"created_at":x.created_at.isoformat()} for x in rows]}

@app.post("/api/staff/uploads/schedule")
async def upload_schedule(file: UploadFile = File(...), user: User = Depends(require("schedules.upload")), db: Session = Depends(db_session)):
    content=await file.read()
    if len(content)>10*1024*1024: raise HTTPException(413,"file_too_large")
    ext=Path(file.filename or "upload").suffix.lower()
    if ext not in (".csv",".xlsx",".xlsm",".pdf"): raise HTTPException(400,"unsupported_file")
    safe_name=f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(4)}{ext}"
    path=UPLOAD_DIR/safe_name; path.write_bytes(content)
    record=ScheduleUpload(filename=file.filename or safe_name,saved_path=str(path),uploaded_by=user.id,status="received")
    db.add(record); db.flush(); imported=0
    if ext != ".pdf":
        try:
            for row in parse_upload_rows(content,file.filename or safe_name):
                sid=studio_from_value(pick(row,"studio","standort","location"),db)
                title=str(pick(row,"kurs","class","title","name") or "Class").strip()
                ctype=str(pick(row,"type","class type","typ") or "Reformer").strip()
                datev=pick(row,"datum","date","tag"); timev=pick(row,"uhrzeit","time","start"); combined=pick(row,"starts_at","start at")
                if combined: starts=date_parser.parse(str(combined))
                elif datev and timev: starts=date_parser.parse(f"{datev} {timev}")
                else: continue
                coach_id=user.coach.id if user.coach and not can(user,"classes.edit") else None
                coach_name=str(pick(row,"coach","trainer","instructor") or "").strip()
                if coach_id is None and coach_name:
                    coach=db.scalar(select(Coach).where(func.lower(Coach.display_name)==coach_name.lower())); coach_id=coach.id if coach else None
                cap=int(pick(row,"capacity","plätze","plaetze","anzahl der plätze") or (db.get(Studio,sid).capacity if sid and db.get(Studio,sid) else 10))
                duration=int(pick(row,"duration","dauer") or 50)
                if not sid: continue
                db.add(ClassSession(studio_id=sid,title=title,class_type=ctype,coach_id=coach_id,starts_at=starts,duration=duration,capacity=cap,created_by=user.id)); imported+=1
            record.status="imported" if imported else "received_no_rows"; record.imported_rows=imported
        except Exception as exc:
            record.status="received_parse_error"
    else:
        record.status="received_pdf"
    db.commit(); return {"ok":True,"status":record.status,"imported_rows":imported}

@app.get("/api/staff/marketing")
def marketing(user: User = Depends(current_user)):
    return {"locked": True, "premium": True, "title": "E-Mail Marketing", "message": "Premium-Modul – als nächstes Upgrade verfügbar."}

@app.get("/api/schedule")
def public_schedule(from_: Optional[str] = None, to: Optional[str] = None, db: Session = Depends(db_session)):
    # FastAPI query alias kept simple: booking frontend can omit range if needed.
    now=datetime.now(timezone.utc)-timedelta(days=1)
    q=select(ClassSession).where(ClassSession.starts_at>=now,ClassSession.status=="active").order_by(ClassSession.starts_at).limit(500)
    rows=db.scalars(q).all()
    return {"classes":[class_dict(c,db) for c in rows]}

@app.post("/api/bookings")
def public_booking(data: PublicBookingIn, db: Session = Depends(db_session)):
    c=db.get(ClassSession,data.classId)
    if not c or c.status!="active": raise HTTPException(409,"class_unavailable")
    reserved=db.scalar(select(func.count(Booking.id)).where(Booking.class_id==c.id,Booking.status=="reserved")) or 0
    if reserved>=c.capacity: raise HTTPException(409,"class_full")
    duplicate=db.scalar(select(Booking).where(Booking.class_id==c.id,Booking.email==data.email.lower(),Booking.status=="reserved"))
    if duplicate: raise HTTPException(409,"duplicate_booking")
    if data.spot:
        spot_taken=db.scalar(select(Booking).where(Booking.class_id==c.id,Booking.spot_number==data.spot,Booking.status=="reserved"))
        if spot_taken: raise HTTPException(409,"spot_taken")
    ref="CP-"+secrets.token_hex(4).upper()
    b=Booking(reference=ref,class_id=c.id,customer_name=(data.firstName+" "+data.lastName).strip(),email=data.email.lower(),phone=data.phone,spot_number=data.spot,payment_method=data.paymentMethod,payment_status="pending",amount_cents=2800 if data.paymentMethod else 0)
    db.add(b);db.commit();return {"booking":{"reference":ref},"payment_status":b.payment_status}

@app.get("/api/bookings")
def public_bookings(email: str, db: Session = Depends(db_session)):
    rows=db.scalars(select(Booking).where(Booking.email==email.lower()).order_by(Booking.created_at.desc())).all()
    return {"credits":0,"bookings":[{"reference":b.reference,"status":b.status,"starts_at":b.klass.starts_at.isoformat(),"name":b.klass.title,"studio_name":b.klass.studio.name,"spot_number":b.spot_number} for b in rows]}

@app.delete("/api/bookings")
def public_cancel(payload: dict, db: Session = Depends(db_session)):
    ref=str(payload.get("reference", "")); email=str(payload.get("email", "")).lower()
    b=db.scalar(select(Booking).where(Booking.reference==ref,Booking.email==email))
    if not b: raise HTTPException(404,"not_found")
    b.status="cancelled";db.commit();return {"ok":True}

@app.post("/api/waitlist")
def join_waitlist(data: WaitlistIn, db: Session = Depends(db_session)):
    c=db.get(ClassSession,data.classId)
    if not c: raise HTTPException(404,"not_found")
    reserved=db.scalar(select(func.count(Booking.id)).where(Booking.class_id==c.id,Booking.status=="reserved")) or 0
    if reserved<c.capacity: raise HTTPException(409,"spots_available")
    existing=db.scalar(select(Waitlist).where(Waitlist.class_id==c.id,Waitlist.email==data.email.lower()))
    if existing: raise HTTPException(409,"already_waitlisted")
    w=Waitlist(class_id=c.id,email=data.email.lower());db.add(w);db.commit()
    pos=db.scalar(select(func.count(Waitlist.id)).where(Waitlist.class_id==c.id,Waitlist.created_at<=w.created_at)) or 1
    return {"position":pos}
