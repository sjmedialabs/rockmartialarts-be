import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from fastapi import FastAPI, HTTPException
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

load_dotenv()

logger = logging.getLogger("essl_service")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())

app = FastAPI(title="ESSL Attendance Middleware", version="1.0.0")

ESSL_URL = (os.getenv("ESSL_URL") or "").strip()
ESSL_SERIAL = (os.getenv("ESSL_SERIAL") or "").strip()
ESSL_USER = (os.getenv("ESSL_USER") or "").strip()
ESSL_PASS = (os.getenv("ESSL_PASS") or "").strip()

MONGO_URI = (os.getenv("MONGO_URI") or "").strip()
MONGO_DB = (os.getenv("ESSL_MONGO_DB") or "attendance_db").strip()
MONGO_COLLECTION = (os.getenv("ESSL_MONGO_COLLECTION") or "logs").strip()
UNMATCHED_COLLECTION = (os.getenv("ESSL_UNMATCHED_COLLECTION") or "unmatched_logs").strip()

# Optional: map logs to app users (same Mongo instance, different db)
APP_DB_NAME = (os.getenv("ESSL_APP_DB_NAME") or os.getenv("DB_NAME") or "marshalats").strip()
APP_USERS_COLLECTION = (os.getenv("ESSL_APP_USERS_COLLECTION") or "users").strip()

ESSL_TIMEOUT_SECS = float(os.getenv("ESSL_TIMEOUT_SECS") or "20")
ESSL_VERIFY_SSL = str(os.getenv("ESSL_VERIFY_SSL") or "true").strip().lower() not in ("0", "false", "no")
ESSL_TZ = (os.getenv("ESSL_TZ") or "Asia/Kolkata").strip()
ESSL_CREATE_USER_URL = (os.getenv("ESSL_CREATE_USER_URL") or "").strip()


def _get_collection() -> Collection:
    if not MONGO_URI:
        raise HTTPException(status_code=500, detail="MONGO_URI is not configured")
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    return db[MONGO_COLLECTION]


def _get_unmatched_collection() -> Collection:
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    return db[UNMATCHED_COLLECTION]


def _get_app_users_collection() -> Optional[Collection]:
    if not MONGO_URI:
        return None
    client = MongoClient(MONGO_URI)
    db = client[APP_DB_NAME]
    return db[APP_USERS_COLLECTION]


def _http_session() -> requests.Session:
    # Keep it simple + reliable: timeout + retry loop (no extra deps).
    s = requests.Session()
    s.trust_env = False
    return s


def _parse_timestamp(value: Any) -> Tuple[datetime, str]:
    """
    Normalize ESSL timestamp to UTC datetime.
    Returns (dt_utc_naive, source_format).
    """
    if value is None:
        raise ValueError("missing timestamp")

    # If device already sends epoch seconds/ms.
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 10_000_000_000:  # ms
            ts = ts / 1000.0
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.replace(tzinfo=None), "epoch"

    s = str(value).strip()
    if not s:
        raise ValueError("empty timestamp")

    # ISO forms
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(ESSL_TZ))
        dt_utc = dt.astimezone(timezone.utc)
        return dt_utc.replace(tzinfo=None), "iso"
    except ValueError:
        pass

    # Common device format fallback: "YYYY-MM-DD HH:MM:SS"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=ZoneInfo(ESSL_TZ))
            dt_utc = dt.astimezone(timezone.utc)
            return dt_utc.replace(tzinfo=None), f"fmt:{fmt}"
        except ValueError:
            continue

    raise ValueError(f"unsupported timestamp format: {s}")


def _normalize_log(record: Dict[str, Any]) -> Dict[str, Any]:
    rid = record.get("id") or record.get("log_id") or record.get("_id")
    if rid is None:
        raise ValueError("missing id/log_id")

    user_id = record.get("user_id") or record.get("userId") or record.get("emp_id")
    if user_id is None:
        raise ValueError("missing user_id")

    ts_utc, ts_src = _parse_timestamp(record.get("timestamp") or record.get("time") or record.get("datetime"))
    typ = str(record.get("type") or record.get("log_type") or "").strip().upper()
    if typ not in ("IN", "OUT"):
        # Keep unknowns but mark them; don't fail entire batch.
        typ = typ or "UNKNOWN"

    device = record.get("device") or record.get("device_name") or record.get("terminal") or None

    return {
        "log_id": str(rid),
        "user_id": str(user_id),
        "timestamp": ts_utc,  # stored as UTC naive datetime (matches existing backend conventions)
        "type": typ,
        "device": device,
        "raw": record,
        "timestamp_source": ts_src,
        "updated_at": datetime.utcnow(),
    }


def _ensure_indexes(coll: Collection) -> None:
    # Dedup primary: stable unique id.
    coll.create_index([("log_id", ASCENDING)], unique=True, name="uniq_log_id")
    # Secondary: guard against vendor bug where log_id is missing/unstable.
    coll.create_index(
        [("user_id", ASCENDING), ("timestamp", ASCENDING), ("type", ASCENDING)],
        unique=True,
        name="uniq_user_ts_type",
        sparse=True,
    )
    coll.create_index([("timestamp", ASCENDING)], name="idx_timestamp")


def _ensure_unmatched_indexes(coll: Collection) -> None:
    coll.create_index([("timestamp", ASCENDING)], name="idx_timestamp")
    coll.create_index([("user_id", ASCENDING), ("timestamp", ASCENDING)], name="idx_user_ts")


@app.on_event("startup")
def _startup() -> None:
    if not ESSL_URL or not ESSL_SERIAL or not ESSL_USER or not ESSL_PASS:
        logger.warning("ESSL config incomplete; /fetch-attendance will fail until env vars are set.")
    try:
        coll = _get_collection()
        _ensure_indexes(coll)
        um = _get_unmatched_collection()
        _ensure_unmatched_indexes(um)
    except Exception:
        logger.exception("Failed to initialize Mongo indexes for ESSL logs")


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "essl_service",
        "db": MONGO_DB,
        "collection": MONGO_COLLECTION,
        "time": datetime.utcnow().isoformat(),
    }


@app.get("/fetch-attendance")
def fetch_attendance() -> Dict[str, Any]:
    if not ESSL_URL or not ESSL_SERIAL or not ESSL_USER or not ESSL_PASS:
        raise HTTPException(status_code=500, detail="ESSL_URL/ESSL_SERIAL/ESSL_USER/ESSL_PASS not configured")

    coll = _get_collection()

    payload = {"serial": ESSL_SERIAL, "username": ESSL_USER, "password": ESSL_PASS}
    sess = _http_session()

    last_err: Optional[str] = None
    resp: Optional[requests.Response] = None
    for attempt in range(1, 4):
        try:
            resp = sess.post(
                ESSL_URL,
                json=payload,
                timeout=ESSL_TIMEOUT_SECS,
                verify=ESSL_VERIFY_SSL,
            )
            break
        except Exception as e:
            last_err = str(e)
            logger.warning("ESSL fetch attempt %s failed: %s", attempt, e)

    if resp is None:
        raise HTTPException(status_code=502, detail=f"ESSL fetch failed: {last_err or 'unknown error'}")

    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"ESSL HTTP {resp.status_code}: {resp.text[:500]}")

    try:
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="ESSL response was not valid JSON")

    raw_logs: List[Dict[str, Any]] = list(data.get("logs") or [])
    upserts = 0
    skipped = 0
    matched = 0
    unmatched = 0
    errors: List[str] = []

    users_coll = _get_app_users_collection()
    unmatched_coll = _get_unmatched_collection()

    for rec in raw_logs:
        try:
            doc = _normalize_log(rec)
            # Attempt mapping: ESSL `user_id` must match app user's `essl_user_id`.
            if users_coll is not None:
                # Admin UI already has `biometric_id`; treat it as the ESSL employee code (user_id).
                u = users_coll.find_one(
                    {
                        "$or": [
                            {"biometric_id": doc["user_id"]},
                            {"essl_user_id": doc["user_id"]},  # backwards compatible
                        ]
                    },
                    {"id": 1, "full_name": 1, "first_name": 1, "last_name": 1, "biometric_id": 1, "essl_user_id": 1},
                )
                if u:
                    doc["app_user_id"] = u.get("id")
                    doc["app_user_name"] = u.get("full_name") or f"{u.get('first_name','')} {u.get('last_name','')}".strip()
                    doc["mapped_by"] = "biometric_id" if u.get("biometric_id") == doc["user_id"] else "essl_user_id"
                    matched += 1
                else:
                    unmatched += 1
                    unmatched_coll.update_one(
                        {"log_id": doc["log_id"]},
                        {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
                        upsert=True,
                    )
            # Two-layer dedupe: prefer log_id, fallback unique tuple.
            # Upsert by log_id; if vendor repeats logs, this becomes idempotent.
            coll.update_one(
                {"log_id": doc["log_id"]},
                {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
                upsert=True,
            )
            upserts += 1
        except Exception as e:
            skipped += 1
            errors.append(str(e))

    return {
        "status": "success",
        "received": len(raw_logs),
        "upserted": upserts,
        "matched_users": matched,
        "unmatched_users": unmatched,
        "skipped": skipped,
        "errors_sample": errors[:10],
    }


@app.post("/create-user")
def create_user(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create/register a user on the ESSL device.
    Expected payload: { "essl_user_id": "STU1001", "name": "Rahul" }
    """
    if not ESSL_URL or not ESSL_SERIAL or not ESSL_USER or not ESSL_PASS:
        raise HTTPException(status_code=500, detail="ESSL_URL/ESSL_SERIAL/ESSL_USER/ESSL_PASS not configured")

    essl_user_id = str(body.get("essl_user_id") or "").strip()
    name = str(body.get("name") or "").strip()
    if not essl_user_id or not name:
        raise HTTPException(status_code=400, detail="essl_user_id and name are required")

    target = ESSL_CREATE_USER_URL or (ESSL_URL.rstrip("/") + "/createuser")
    payload = {
        "serial": ESSL_SERIAL,
        "username": ESSL_USER,
        "password": ESSL_PASS,
        "user_id": essl_user_id,
        "name": name,
    }
    sess = _http_session()
    try:
        resp = sess.post(target, json=payload, timeout=ESSL_TIMEOUT_SECS, verify=ESSL_VERIFY_SSL)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ESSL create-user request failed: {e}")

    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"ESSL create-user HTTP {resp.status_code}: {resp.text[:500]}")
    try:
        return resp.json()
    except Exception:
        return {"status": "ok", "raw": resp.text[:1000]}
