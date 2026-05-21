"""
CroixAI Key Server — Owner-side license validation backend.
Deploy this on any VPS. Customers never see this code.

Endpoints:
  POST /v1/validate          — called by CroixAI.exe on customer machine
  POST /admin/keys/generate  — owner generates a new key
  GET  /admin/keys           — owner lists all keys
  POST /admin/keys/{key}/revoke  — owner revokes a key

Run:  uvicorn server:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import hashlib
import os
import random
import secrets
import sqlite3
import string
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DB_PATH      = Path(__file__).parent / "keys.db"
ADMIN_SECRET = os.environ.get("CROIXAI_ADMIN_SECRET", "change-this-secret-in-production")
PRODUCT_ID   = "CROIXAI_V1"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

def _init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS license_keys (
                key          TEXT PRIMARY KEY,
                hwid         TEXT,               -- NULL until first activation
                created_at   TEXT NOT NULL,
                expires_at   TEXT,               -- NULL = lifetime
                revoked      INTEGER DEFAULT 0,
                note         TEXT,               -- owner note (e.g. customer name)
                last_seen    TEXT
            )
        """)
        conn.commit()

_init_db()


@contextmanager
def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Key generation
# ---------------------------------------------------------------------------

def _gen_key() -> str:
    """Generate CROIX-XXXX-XXXX-XXXX-XXXX format key."""
    alphabet = string.ascii_uppercase + string.digits
    alphabet = alphabet.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    groups = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4)]
    return "CROIX-" + "-".join(groups)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="CroixAI Key Server", docs_url=None, redoc_url=None)


def _require_admin(x_admin_secret: str = Header(None)):
    if x_admin_secret != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")


# ---------------------------------------------------------------------------
# Validation endpoint (called by CroixAI.exe)
# ---------------------------------------------------------------------------

class ValidateRequest(BaseModel):
    key:     str
    hwid:    str
    product: str
    version: str = "1.0"


@app.post("/v1/validate")
def validate_key(req: ValidateRequest):
    if req.product != PRODUCT_ID:
        return {"valid": False, "hwid_ok": False, "message": "Ungültiges Produkt."}

    now_str = datetime.now(timezone.utc).isoformat()

    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM license_keys WHERE key = ?", (req.key,)
        ).fetchone()

        if row is None:
            return {"valid": False, "hwid_ok": False, "message": "Ungültiger Key."}

        if row["revoked"]:
            return {"valid": False, "hwid_ok": False, "message": "Key wurde gesperrt."}

        # Check expiry
        if row["expires_at"]:
            exp = datetime.fromisoformat(row["expires_at"])
            if exp < datetime.now(timezone.utc):
                return {"valid": False, "hwid_ok": False, "message": "Key abgelaufen."}

        # HWID check / auto-bind
        hwid_ok = True
        if row["hwid"] is None:
            # First activation — bind HWID automatically
            conn.execute(
                "UPDATE license_keys SET hwid=?, last_seen=? WHERE key=?",
                (req.hwid, now_str, req.key),
            )
            conn.commit()
        elif row["hwid"] != req.hwid:
            # Different machine — deny
            hwid_ok = False

        if hwid_ok:
            conn.execute(
                "UPDATE license_keys SET last_seen=? WHERE key=?",
                (now_str, req.key),
            )
            conn.commit()

    if not hwid_ok:
        return {
            "valid":    True,
            "hwid_ok":  False,
            "message":  "Key ist bereits auf einer anderen Hardware aktiviert.",
        }

    expires = row["expires_at"]
    return {
        "valid":      True,
        "hwid_ok":    True,
        "expires_at": expires,
        "message":    "Lizenz aktiv.",
    }


# ---------------------------------------------------------------------------
# Admin endpoints (owner only)
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    note:       Optional[str] = None
    expires_in_days: Optional[int] = None   # None = lifetime


@app.post("/admin/keys/generate", dependencies=[Depends(_require_admin)])
def generate_key(req: GenerateRequest = GenerateRequest()):
    key = _gen_key()
    now = datetime.now(timezone.utc)
    expires = None
    if req.expires_in_days:
        expires = (now + timedelta(days=req.expires_in_days)).isoformat()

    with _db() as conn:
        conn.execute(
            "INSERT INTO license_keys (key, created_at, expires_at, note) VALUES (?,?,?,?)",
            (key, now.isoformat(), expires, req.note),
        )
        conn.commit()

    return {"key": key, "expires_at": expires, "note": req.note}


@app.get("/admin/keys", dependencies=[Depends(_require_admin)])
def list_keys():
    with _db() as conn:
        rows = conn.execute(
            "SELECT key, hwid, created_at, expires_at, revoked, note, last_seen "
            "FROM license_keys ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@app.post("/admin/keys/{key}/revoke", dependencies=[Depends(_require_admin)])
def revoke_key(key: str):
    with _db() as conn:
        updated = conn.execute(
            "UPDATE license_keys SET revoked=1 WHERE key=?", (key,)
        ).rowcount
        conn.commit()
    if not updated:
        raise HTTPException(404, "Key nicht gefunden.")
    return {"revoked": True, "key": key}


@app.post("/admin/keys/{key}/reset-hwid", dependencies=[Depends(_require_admin)])
def reset_hwid(key: str):
    """Reset HWID binding so key can be activated on a new machine."""
    with _db() as conn:
        updated = conn.execute(
            "UPDATE license_keys SET hwid=NULL WHERE key=?", (key,)
        ).rowcount
        conn.commit()
    if not updated:
        raise HTTPException(404, "Key nicht gefunden.")
    return {"hwid_reset": True, "key": key}
