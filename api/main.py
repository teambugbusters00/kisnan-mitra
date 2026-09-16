import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
import psycopg2
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET", "change-this-in-production")
JWT_ALGORITHM = "HS256"

app = FastAPI(title="KisanLink API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  phone VARCHAR(30) UNIQUE NOT NULL,
  email VARCHAR(160) UNIQUE,
  role VARCHAR(20) NOT NULL DEFAULT 'farmer' CHECK (role IN ('farmer','buyer','fpo','admin')),
  password_hash TEXT NOT NULL,
  location VARCHAR(160),
  kyc_verified BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS produce_listings (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  crop VARCHAR(120) NOT NULL,
  variety VARCHAR(120),
  quantity NUMERIC(12,2) NOT NULL,
  unit VARCHAR(30) NOT NULL DEFAULT 'qtl',
  asking_price NUMERIC(12,2),
  grade VARCHAR(60),
  mandi VARCHAR(160),
  status VARCHAR(30) NOT NULL DEFAULT 'active',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS offers (
  id SERIAL PRIMARY KEY,
  listing_id INTEGER NOT NULL REFERENCES produce_listings(id) ON DELETE CASCADE,
  buyer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  price NUMERIC(12,2) NOT NULL,
  quantity NUMERIC(12,2) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS transactions (
  id SERIAL PRIMARY KEY,
  listing_id INTEGER REFERENCES produce_listings(id) ON DELETE SET NULL,
  buyer_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  farmer_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  amount NUMERIC(14,2) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS notifications (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(180) NOT NULL,
  message TEXT NOT NULL,
  read BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

class AuthIn(BaseModel):
    phone: str
    password: str
    role: str = "farmer"

class RegisterIn(BaseModel):
    name: str
    phone: str
    password: str = Field(min_length=6)
    role: str = "farmer"
    email: Optional[str] = None
    location: Optional[str] = None

class ListingIn(BaseModel):
    crop: str
    variety: Optional[str] = None
    quantity: float
    unit: str = "qtl"
    asking_price: Optional[float] = None
    grade: Optional[str] = None
    mandi: Optional[str] = None

class OfferIn(BaseModel):
    listing_id: int
    price: float
    quantity: float


def conn():
    if not DATABASE_URL:
        raise HTTPException(500, "DATABASE_URL is not configured")
    return psycopg2.connect(DATABASE_URL)


def init_db():
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(SCHEMA)


def token_for(user_id: int, role: str):
    return jwt.encode({"sub": str(user_id), "role": role, "exp": datetime.now(timezone.utc) + timedelta(days=7)}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def current_user(authorization: Optional[str]):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Bearer token required")
    try:
        return jwt.decode(authorization.split(" ", 1)[1], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")


@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health():
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("SELECT 1")
    return {"ok": True, "service": "kisanlink-api"}

@app.post("/api/auth/register")
def register(body: RegisterIn):
    role = body.role if body.role in {"farmer", "buyer", "fpo"} else "farmer"
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    try:
        with conn() as c:
            with c.cursor() as cur:
                cur.execute("INSERT INTO users(name,phone,password_hash,role,email,location,kyc_verified) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING id", (body.name, body.phone, hashed, role, body.email, body.location, False))
                uid = cur.fetchone()[0]
                cur.execute("INSERT INTO notifications(user_id,title,message) VALUES(%s,%s,%s)", (uid, "Welcome to KisanLink", "Your account is ready. Complete KYC to unlock verified trading."))
        return {"token": token_for(uid, role), "user": {"id": uid, "name": body.name, "phone": body.phone, "role": role}}
    except psycopg2.errors.UniqueViolation:
        raise HTTPException(409, "Phone or email already registered")

@app.post("/api/auth/login")
def login(body: AuthIn):
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("SELECT id,name,phone,email,role,password_hash,location,kyc_verified FROM users WHERE phone=%s", (body.phone,))
            row = cur.fetchone()
    if not row or not bcrypt.checkpw(body.password.encode(), row[5].encode()):
        raise HTTPException(401, "Invalid mobile number or password")
    if body.role != row[4] and body.role != "admin":
        raise HTTPException(403, "Account role does not match selected role")
    return {"token": token_for(row[0], row[4]), "user": {"id": row[0], "name": row[1], "phone": row[2], "email": row[3], "role": row[4], "location": row[6], "kyc_verified": row[7]}}

@app.get("/api/me")
def me(authorization: Optional[str] = Header(None)):
    u = current_user(authorization)
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("SELECT id,name,phone,email,role,location,kyc_verified,created_at FROM users WHERE id=%s", (int(u["sub"]),))
            row = cur.fetchone()
    if not row: raise HTTPException(404, "User not found")
    return dict(zip(["id","name","phone","email","role","location","kyc_verified","created_at"], row))

@app.get("/api/market/prices")
def market_prices():
    return {"source": "KisanLink demo market feed", "updated_at": datetime.now(timezone.utc).isoformat(), "prices": [
        {"crop":"Wheat (Sharbati)","price":2425,"unit":"qtl","trend":2.8,"mandi":"Indore APMC"},
        {"crop":"Soybean (Yellow)","price":4650,"unit":"qtl","trend":1.2,"mandi":"Indore APMC"},
        {"crop":"Tomato (Hybrid Red)","price":1220,"unit":"crate","trend":5.4,"mandi":"Choithram Mandi"},
        {"crop":"Onion (Nashik Red)","price":1650,"unit":"qtl","trend":-2.1,"mandi":"Indore APMC"}
    ]}

@app.post("/api/listings")
def create_listing(body: ListingIn, authorization: Optional[str] = Header(None)):
    u = current_user(authorization)
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("INSERT INTO produce_listings(user_id,crop,variety,quantity,unit,asking_price,grade,mandi) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id", (int(u["sub"]), body.crop, body.variety, body.quantity, body.unit, body.asking_price, body.grade, body.mandi))
            lid = cur.fetchone()[0]
    return {"id": lid, "status": "active"}

@app.get("/api/listings")
def listings(authorization: Optional[str] = Header(None)):
    u = current_user(authorization)
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("SELECT id,crop,variety,quantity,unit,asking_price,grade,mandi,status,created_at FROM produce_listings WHERE user_id=%s ORDER BY created_at DESC", (int(u["sub"]),))
            rows = cur.fetchall()
    keys=["id","crop","variety","quantity","unit","asking_price","grade","mandi","status","created_at"]
    return [dict(zip(keys,r)) for r in rows]

@app.post("/api/offers")
def make_offer(body: OfferIn, authorization: Optional[str] = Header(None)):
    u=current_user(authorization)
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("INSERT INTO offers(listing_id,buyer_id,price,quantity) VALUES(%s,%s,%s,%s) RETURNING id", (body.listing_id,int(u["sub"]),body.price,body.quantity))
            oid=cur.fetchone()[0]
            cur.execute("SELECT user_id FROM produce_listings WHERE id=%s", (body.listing_id,))
            owner=cur.fetchone()
            if owner:
                cur.execute("INSERT INTO notifications(user_id,title,message) VALUES(%s,%s,%s)", (owner[0], "New buyer offer", f"New offer of ₹{body.price}/unit for your listing."))
    return {"id": oid, "status":"pending"}

@app.get("/api/notifications")
def notifications(authorization: Optional[str] = Header(None)):
    u=current_user(authorization)
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("SELECT id,title,message,read,created_at FROM notifications WHERE user_id=%s ORDER BY created_at DESC", (int(u["sub"]),))
            rows=cur.fetchall()
    return [dict(zip(["id","title","message","read","created_at"],r)) for r in rows]

@app.get("/api/transactions")
def transactions(authorization: Optional[str] = Header(None)):
    u=current_user(authorization)
    uid=int(u["sub"])
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("SELECT id,listing_id,buyer_id,farmer_id,amount,status,created_at FROM transactions WHERE buyer_id=%s OR farmer_id=%s ORDER BY created_at DESC", (uid,uid))
            rows=cur.fetchall()
    return [dict(zip(["id","listing_id","buyer_id","farmer_id","amount","status","created_at"],r)) for r in rows]
