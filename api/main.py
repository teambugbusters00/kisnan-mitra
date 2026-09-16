import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
import psycopg2
import requests
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DATABASE_URL=os.getenv("DATABASE_URL")
JWT_SECRET=os.getenv("JWT_SECRET","change-this-in-production")
JWT_ALGORITHM="HS256"
DATA_GOV_API_KEY=os.getenv("DATA_GOV_API_KEY","").strip()
AGMARKNET_RESOURCE="9ef84268-d588-465a-a308-a864a43d0070"
OPEN_METEO_URL="https://api.open-meteo.com/v1/forecast"
TWILIO_ACCOUNT_SID=os.getenv("TWILIO_ACCOUNT_SID","").strip()
TWILIO_AUTH_TOKEN=os.getenv("TWILIO_AUTH_TOKEN","").strip()
TWILIO_VERIFY_SERVICE_SID=os.getenv("TWILIO_VERIFY_SERVICE_SID","").strip()
RAZORPAY_KEY_ID=os.getenv("RAZORPAY_KEY_ID","").strip()
RAZORPAY_KEY_SECRET=os.getenv("RAZORPAY_KEY_SECRET","").strip()
RAZORPAY_WEBHOOK_SECRET=os.getenv("RAZORPAY_WEBHOOK_SECRET","").strip()
VISION_API_URL=os.getenv("VISION_API_URL","").strip()
VISION_API_TOKEN=os.getenv("VISION_API_TOKEN","").strip()

app=FastAPI(title="KisanLink API",version="2.0.0")
app.add_middleware(CORSMiddleware,allow_origins=[o.strip() for o in os.getenv("CORS_ORIGINS","*").split(",")],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

SCHEMA="""
CREATE TABLE IF NOT EXISTS users(id SERIAL PRIMARY KEY,name VARCHAR(120) NOT NULL,phone VARCHAR(30) UNIQUE NOT NULL,email VARCHAR(160) UNIQUE,role VARCHAR(20) NOT NULL DEFAULT 'farmer',password_hash TEXT NOT NULL,location VARCHAR(240),latitude DOUBLE PRECISION,longitude DOUBLE PRECISION,kyc_verified BOOLEAN NOT NULL DEFAULT FALSE,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE IF NOT EXISTS produce_listings(id SERIAL PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,crop VARCHAR(120) NOT NULL,variety VARCHAR(120),quantity NUMERIC(12,2) NOT NULL,unit VARCHAR(30) NOT NULL DEFAULT 'qtl',asking_price NUMERIC(12,2),grade VARCHAR(60),mandi VARCHAR(160),status VARCHAR(30) NOT NULL DEFAULT 'active',created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE IF NOT EXISTS offers(id SERIAL PRIMARY KEY,listing_id INTEGER NOT NULL REFERENCES produce_listings(id) ON DELETE CASCADE,buyer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,price NUMERIC(12,2) NOT NULL,quantity NUMERIC(12,2) NOT NULL,status VARCHAR(30) NOT NULL DEFAULT 'pending',created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE IF NOT EXISTS transactions(id SERIAL PRIMARY KEY,listing_id INTEGER REFERENCES produce_listings(id) ON DELETE SET NULL,buyer_id INTEGER REFERENCES users(id) ON DELETE SET NULL,farmer_id INTEGER REFERENCES users(id) ON DELETE SET NULL,amount NUMERIC(14,2) NOT NULL,status VARCHAR(30) NOT NULL DEFAULT 'pending',provider VARCHAR(40),provider_ref VARCHAR(160),created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE IF NOT EXISTS notifications(id SERIAL PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,title VARCHAR(180) NOT NULL,message TEXT NOT NULL,read BOOLEAN NOT NULL DEFAULT FALSE,created_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
CREATE TABLE IF NOT EXISTS device_tokens(id SERIAL PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,token TEXT NOT NULL,platform VARCHAR(30),created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),UNIQUE(user_id,token));
"""

class AuthIn(BaseModel): phone:str; password:str; role:str="farmer"
class RegisterIn(BaseModel): name:str; phone:str; password:str=Field(min_length=6); role:str="farmer"; email:Optional[str]=None; location:Optional[str]=None
class ListingIn(BaseModel): crop:str; variety:Optional[str]=None; quantity:float; unit:str="qtl"; asking_price:Optional[float]=None; grade:Optional[str]=None; mandi:Optional[str]=None
class OfferIn(BaseModel): listing_id:int; price:float; quantity:float
class LocationIn(BaseModel): latitude:float; longitude:float; label:Optional[str]=None
class OtpIn(BaseModel): phone:str; code:Optional[str]=None
class DeviceTokenIn(BaseModel): token:str; platform:str="android"

def conn():
    if not DATABASE_URL: raise HTTPException(500,"DATABASE_URL is not configured")
    return psycopg2.connect(DATABASE_URL)

def token_for(uid:int,role:str): return jwt.encode({"sub":str(uid),"role":role,"exp":datetime.now(timezone.utc)+timedelta(days=7)},JWT_SECRET,algorithm=JWT_ALGORITHM)
def current_user(authorization:Optional[str]):
    if not authorization or not authorization.lower().startswith("bearer "): raise HTTPException(401,"Bearer token required")
    try: return jwt.decode(authorization.split(" ",1)[1],JWT_SECRET,algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError: raise HTTPException(401,"Invalid or expired token")
def user_id(authorization): return int(current_user(authorization)["sub"])

@app.on_event("startup")
def startup():
    with conn() as c:
        with c.cursor() as cur:
            cur.execute(SCHEMA)
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS provider VARCHAR(40)")
            cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS provider_ref VARCHAR(160)")

@app.get("/health")
def health():
    with conn() as c:
        with c.cursor() as cur: cur.execute("SELECT 1")
    return {"ok":True,"service":"kisanlink-api","version":"2.0.0"}

@app.get("/api/integrations/status")
def integration_status():
    return {"market_data":bool(DATA_GOV_API_KEY),"weather":True,"device_location":True,"otp":bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_VERIFY_SERVICE_SID),"vision":bool(VISION_API_URL),"payments":bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET),"dbt_escrow":False,"kyc":False,"fpo":False,"warehouse":False,"push":False}

@app.post("/api/auth/register")
def register(body:RegisterIn):
    role=body.role if body.role in {"farmer","buyer","fpo"} else "farmer"; hashed=bcrypt.hashpw(body.password.encode(),bcrypt.gensalt()).decode()
    try:
        with conn() as c:
            with c.cursor() as cur:
                cur.execute("INSERT INTO users(name,phone,password_hash,role,email,location) VALUES(%s,%s,%s,%s,%s,%s) RETURNING id",(body.name,body.phone,hashed,role,body.email,body.location)); uid=cur.fetchone()[0]
                cur.execute("INSERT INTO notifications(user_id,title,message) VALUES(%s,%s,%s)",(uid,"Welcome to KisanLink","Account created. Complete provider-backed verification when available."))
        tok=token_for(uid,role); return {"token":tok,"access_token":tok,"user":{"id":uid,"name":body.name,"phone":body.phone,"role":role,"kyc_verified":False}}
    except psycopg2.errors.UniqueViolation: raise HTTPException(409,"Phone or email already registered")

@app.post("/api/auth/login")
def login(body:AuthIn):
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("SELECT id,name,phone,email,role,password_hash,location,kyc_verified FROM users WHERE phone=%s",(body.phone,)); row=cur.fetchone()
    if not row or not bcrypt.checkpw(body.password.encode(),row[5].encode()): raise HTTPException(401,"Invalid mobile number or password")
    if body.role!=row[4] and body.role!="admin": raise HTTPException(403,"Account role does not match selected role")
    tok=token_for(row[0],row[4]); return {"token":tok,"access_token":tok,"user":{"id":row[0],"name":row[1],"phone":row[2],"email":row[3],"role":row[4],"location":row[6],"kyc_verified":row[7]}}

@app.get("/api/me")
def me(authorization:Optional[str]=Header(None)):
    uid=user_id(authorization)
    with conn() as c:
        with c.cursor() as cur: cur.execute("SELECT id,name,phone,email,role,location,latitude,longitude,kyc_verified,created_at FROM users WHERE id=%s",(uid,)); row=cur.fetchone()
    if not row: raise HTTPException(404,"User not found")
    return dict(zip(["id","name","phone","email","role","location","latitude","longitude","kyc_verified","created_at"],row))

@app.get("/api/market/prices")
def market_prices(state:Optional[str]=None,commodity:Optional[str]=None,market:Optional[str]=None,limit:int=50):
    if not DATA_GOV_API_KEY: return {"live":False,"source":"data.gov.in","message":"DATA_GOV_API_KEY is not configured","prices":[]}
    params={"api-key":DATA_GOV_API_KEY,"format":"json","limit":min(max(limit,1),1000)}
    if state: params["filters[state.keyword]"]=state
    if commodity: params["filters[commodity]"]=commodity
    if market: params["filters[market]"]=market
    try:
        r=requests.get(f"https://api.data.gov.in/resource/{AGMARKNET_RESOURCE}",params=params,timeout=12); r.raise_for_status(); raw=r.json(); now=datetime.now(timezone.utc).isoformat(); out=[]
        for x in raw.get("records",[]): out.append({"state":x.get("state"),"district":x.get("district"),"mandi":x.get("market"),"crop":x.get("commodity"),"variety":x.get("variety"),"grade":x.get("grade"),"arrival_date":x.get("arrival_date"),"min_price":float(x.get("min_price") or 0),"max_price":float(x.get("max_price") or 0),"modal_price":float(x.get("modal_price") or 0),"unit":"qtl","source":"AGMARKNET/data.gov.in","updated_at":now})
        return {"live":True,"source":"AGMARKNET/data.gov.in","count":len(out),"prices":out}
    except Exception as e: raise HTTPException(502,f"Market data provider unavailable: {e}")

@app.get("/api/market/insight")
def market_insight(commodity:Optional[str]=None,state:Optional[str]=None):
    data=market_prices(state=state,commodity=commodity,limit=100); prices=data.get("prices",[])
    if not prices: return {"live":False,"message":"No live market observations available"}
    valid=[p for p in prices if p["modal_price"]>0]; hi=max(valid,key=lambda p:p["modal_price"]) if valid else None; lo=min(valid,key=lambda p:p["modal_price"]) if valid else None
    return {"live":True,"observations":len(prices),"average_modal":round(sum(p["modal_price"] for p in valid)/len(valid),2) if valid else None,"highest":hi,"lowest":lo,"spread":round(hi["modal_price"]-lo["modal_price"],2) if hi and lo else None}

@app.get("/api/weather")
def weather(latitude:float,longitude:float):
    try:
        params={"latitude":latitude,"longitude":longitude,"current":"temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m","daily":"temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum","forecast_days":5,"timezone":"auto"}; r=requests.get(OPEN_METEO_URL,params=params,timeout=10); r.raise_for_status(); d=r.json()
        return {"source":"Open-Meteo","latitude":d.get("latitude"),"longitude":d.get("longitude"),"current":d.get("current"),"daily":d.get("daily"),"timezone":d.get("timezone")}
    except Exception as e: raise HTTPException(502,f"Weather provider unavailable: {e}")

@app.post("/api/location")
def save_location(body:LocationIn,authorization:Optional[str]=Header(None)):
    uid=user_id(authorization)
    with conn() as c:
        with c.cursor() as cur: cur.execute("UPDATE users SET location=%s,latitude=%s,longitude=%s WHERE id=%s",(body.label,body.latitude,body.longitude,uid))
    return {"saved":True,"latitude":body.latitude,"longitude":body.longitude,"label":body.label}

@app.post("/api/listings")
def create_listing(body:ListingIn,authorization:Optional[str]=Header(None)):
    uid=user_id(authorization)
    with conn() as c:
        with c.cursor() as cur: cur.execute("INSERT INTO produce_listings(user_id,crop,variety,quantity,unit,asking_price,grade,mandi) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id,created_at",(uid,body.crop,body.variety,body.quantity,body.unit,body.asking_price,body.grade,body.mandi)); lid,created=cur.fetchone()
    return {"id":lid,"status":"active","created_at":created}

@app.get("/api/listings/my")
@app.get("/api/listings")
def my_listings(authorization:Optional[str]=Header(None)):
    uid=user_id(authorization)
    with conn() as c:
        with c.cursor() as cur: cur.execute("SELECT id,crop,variety,quantity,unit,asking_price,grade,mandi,status,created_at FROM produce_listings WHERE user_id=%s ORDER BY created_at DESC",(uid,)); rows=cur.fetchall()
    return [dict(zip(["id","crop","variety","quantity","unit","asking_price","grade","mandi","status","created_at"],r)) for r in rows]

@app.post("/api/offers")
def make_offer(body:OfferIn,authorization:Optional[str]=Header(None)):
    uid=user_id(authorization)
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("INSERT INTO offers(listing_id,buyer_id,price,quantity) VALUES(%s,%s,%s,%s) RETURNING id",(body.listing_id,uid,body.price,body.quantity)); oid=cur.fetchone()[0]
            cur.execute("SELECT user_id,crop FROM produce_listings WHERE id=%s",(body.listing_id)); owner=cur.fetchone()
            if owner: cur.execute("INSERT INTO notifications(user_id,title,message) VALUES(%s,%s,%s)",(owner[0],"New buyer offer",f"New offer of ₹{body.price}/qtl for your {owner[1]} listing."))
    return {"id":oid,"status":"pending"}

@app.get("/api/offers/my")
def offers_my(authorization:Optional[str]=Header(None)):
    uid=user_id(authorization)
    with conn() as c:
        with c.cursor() as cur:
            cur.execute("SELECT o.id,o.listing_id,o.price,o.quantity,o.status,o.created_at,u.name buyer_name,p.crop,p.unit FROM offers o JOIN users u ON u.id=o.buyer_id JOIN produce_listings p ON p.id=o.listing_id WHERE p.user_id=%s OR o.buyer_id=%s ORDER BY o.created_at DESC",(uid,uid)); rows=cur.fetchall()
    return [dict(zip(["id","listing_id","price","quantity","status","created_at","buyer_name","crop","unit"],r)) for r in rows]

@app.get("/api/transactions/my")
@app.get("/api/transactions")
def transactions(authorization:Optional[str]=Header(None)):
    uid=user_id(authorization)
    with conn() as c:
        with c.cursor() as cur: cur.execute("SELECT id,listing_id,buyer_id,farmer_id,amount,status,provider,provider_ref,created_at FROM transactions WHERE buyer_id=%s OR farmer_id=%s ORDER BY created_at DESC",(uid,uid)); rows=cur.fetchall()
    return [dict(zip(["id","listing_id","buyer_id","farmer_id","amount","status","provider","provider_ref","created_at"],r)) for r in rows]

@app.get("/api/notifications")
def notifications(authorization:Optional[str]=Header(None)):
    uid=user_id(authorization)
    with conn() as c:
        with c.cursor() as cur: cur.execute("SELECT id,title,message,read,created_at FROM notifications WHERE user_id=%s ORDER BY created_at DESC",(uid,)); rows=cur.fetchall()
    return [dict(zip(["id","title","message","read","created_at"],r)) for r in rows]

@app.post("/api/devices/register")
def register_device(body:DeviceTokenIn,authorization:Optional[str]=Header(None)):
    uid=user_id(authorization)
    with conn() as c:
        with c.cursor() as cur: cur.execute("INSERT INTO device_tokens(user_id,token,platform) VALUES(%s,%s,%s) ON CONFLICT(user_id,token) DO UPDATE SET platform=EXCLUDED.platform",(uid,body.token,body.platform))
    return {"registered":True}

@app.post("/api/otp/send")
def otp_send(body:OtpIn):
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_VERIFY_SERVICE_SID): raise HTTPException(503,"OTP provider is not configured")
    from twilio.rest import Client
    try: v=Client(TWILIO_ACCOUNT_SID,TWILIO_AUTH_TOKEN).verify.v2.services(TWILIO_VERIFY_SERVICE_SID).verifications.create(to=body.phone,channel="sms"); return {"sent":True,"status":v.status}
    except Exception as e: raise HTTPException(502,f"OTP provider error: {e}")

@app.post("/api/otp/verify")
def otp_verify(body:OtpIn):
    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_VERIFY_SERVICE_SID): raise HTTPException(503,"OTP provider is not configured")
    if not body.code: raise HTTPException(400,"OTP code is required")
    from twilio.rest import Client
    try: v=Client(TWILIO_ACCOUNT_SID,TWILIO_AUTH_TOKEN).verify.v2.services(TWILIO_VERIFY_SERVICE_SID).verification_checks.create(to=body.phone,code=body.code); return {"verified":v.status=="approved","status":v.status}
    except Exception as e: raise HTTPException(502,f"OTP provider error: {e}")

@app.post("/api/vision/analyze")
async def vision_analyze(file:UploadFile=File(...),authorization:Optional[str]=Header(None)):
    user_id(authorization)
    if not VISION_API_URL: raise HTTPException(503,"Computer-vision provider is not configured")
    data=await file.read(); headers={"Authorization":f"Bearer {VISION_API_TOKEN}"} if VISION_API_TOKEN else {}
    try:
        r=requests.post(VISION_API_URL,files={"file":(file.filename,data,file.content_type or "application/octet-stream")},headers=headers,timeout=30); r.raise_for_status(); return {"provider":"configured-vision-api","result":r.json()}
    except Exception as e: raise HTTPException(502,f"Vision provider error: {e}")

@app.post("/api/payments/verify")
def verify_payment(payload:dict):
    if not RAZORPAY_KEY_SECRET: raise HTTPException(503,"Payment provider is not configured")
    order_id=payload.get("razorpay_order_id"); payment_id=payload.get("razorpay_payment_id"); signature=payload.get("razorpay_signature")
    if not all([order_id,payment_id,signature]): raise HTTPException(400,"Missing Razorpay payment fields")
    expected=hmac.new(RAZORPAY_KEY_SECRET.encode(),f"{order_id}|{payment_id}".encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,signature): raise HTTPException(400,"Invalid payment signature")
    return {"verified":True,"provider":"razorpay"}

@app.post("/api/payments/webhook")
def payment_webhook(payload:dict,x_razorpay_signature:Optional[str]=Header(None)):
    if not RAZORPAY_WEBHOOK_SECRET: raise HTTPException(503,"Payment webhook secret is not configured")
    raw=json.dumps(payload,separators=(",",":"),ensure_ascii=False).encode(); expected=hmac.new(RAZORPAY_WEBHOOK_SECRET.encode(),raw,hashlib.sha256).hexdigest()
    if not x_razorpay_signature or not hmac.compare_digest(expected,x_razorpay_signature): raise HTTPException(400,"Invalid webhook signature")
    return {"received":True}
