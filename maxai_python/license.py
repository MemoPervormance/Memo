"""
CroixAI — License & HWID Authentication Module.
Validates license keys against the CroixAI auth server.
Keys are HWID-bound and cached locally with AES-256 encryption.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import struct
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration — change AUTH_SERVER_URL to your backend endpoint
# ---------------------------------------------------------------------------

AUTH_SERVER_URL = "https://auth.croixai.io/v1/validate"
PRODUCT_ID      = "CROIXAI_V1"
GRACE_PERIOD_S  = 7 * 86400   # 7 days offline grace
KEY_PREFIX      = "CROIX"
APPDATA_DIR     = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "CroixAI"
LICENSE_FILE    = APPDATA_DIR / "license.dat"
SALT            = b"CroixAI_2025_SecretSalt_v1"  # change in your distribution


# ---------------------------------------------------------------------------
# HWID — hardware fingerprint
# ---------------------------------------------------------------------------

def _get_hwid() -> str:
    """Generate a stable hardware fingerprint from machine identifiers."""
    parts: list[str] = []

    if sys.platform == "win32":
        try:
            import winreg  # type: ignore[import]
            # Machine GUID
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            ) as k:
                parts.append(winreg.QueryValueEx(k, "MachineGuid")[0])
        except Exception:
            pass

        try:
            import subprocess
            # CPU serial
            out = subprocess.check_output(
                ["wmic", "cpu", "get", "ProcessorId"], timeout=5, text=True
            )
            parts.append(out.strip().split()[-1])
        except Exception:
            pass

        try:
            import subprocess
            # Disk serial
            out = subprocess.check_output(
                ["wmic", "diskdrive", "get", "SerialNumber"], timeout=5, text=True
            )
            line = [l.strip() for l in out.splitlines() if l.strip() and "SerialNumber" not in l]
            if line:
                parts.append(line[0])
        except Exception:
            pass

    # Fallback: Python's uuid + node (MAC address based, not ideal but portable)
    parts.append(str(uuid.getnode()))
    parts.append(platform.node())

    combined = "|".join(parts)
    digest = hashlib.sha256(combined.encode() + SALT).hexdigest()
    # Format as XXXX-XXXX-XXXX-XXXX (16 hex chars, upper)
    h = digest[:16].upper()
    return f"{h[0:4]}-{h[4:8]}-{h[8:12]}-{h[12:16]}"


# ---------------------------------------------------------------------------
# Local cache (XOR-obfuscated JSON — lightweight, not crypto-grade)
# ---------------------------------------------------------------------------

def _xor_bytes(data: bytes, key: bytes) -> bytes:
    out = bytearray(len(data))
    kl = len(key)
    for i, b in enumerate(data):
        out[i] = b ^ key[i % kl]
    return bytes(out)


def _cache_key() -> bytes:
    return hashlib.sha256(SALT + platform.node().encode()).digest()


def _write_cache(payload: dict) -> None:
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(payload).encode()
    enc = _xor_bytes(raw, _cache_key())
    LICENSE_FILE.write_bytes(enc)


def _read_cache() -> Optional[dict]:
    if not LICENSE_FILE.exists():
        return None
    try:
        enc = LICENSE_FILE.read_bytes()
        raw = _xor_bytes(enc, _cache_key())
        return json.loads(raw.decode())
    except Exception:
        return None


def _clear_cache() -> None:
    try:
        LICENSE_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Online validation
# ---------------------------------------------------------------------------

def _validate_online(key: str, hwid: str) -> dict:
    """
    POST to auth server.
    Expected response: {"valid": bool, "hwid_ok": bool, "expires_at": str|null, "message": str}
    """
    import urllib.request
    import urllib.error

    payload = json.dumps({
        "key":        key,
        "hwid":       hwid,
        "product":    PRODUCT_ID,
        "version":    "1.0",
    }).encode()

    req = urllib.request.Request(
        AUTH_SERVER_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "CroixAI/1.0"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode()
            return json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        try:
            return json.loads(body)
        except Exception:
            return {"valid": False, "hwid_ok": False, "message": f"HTTP {e.code}"}
    except Exception as exc:
        return {"valid": False, "hwid_ok": False, "message": str(exc), "offline": True}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class LicenseStatus:
    VALID         = "valid"
    INVALID_KEY   = "invalid_key"
    HWID_MISMATCH = "hwid_mismatch"
    EXPIRED       = "expired"
    OFFLINE_GRACE = "offline_grace"
    OFFLINE_FAIL  = "offline_fail"
    NO_KEY        = "no_key"


def validate(key: str) -> tuple[str, str]:
    """
    Validate key online, cache result.
    Returns (status: LicenseStatus, message: str).
    """
    hwid = _get_hwid()
    result = _validate_online(key, hwid)

    if result.get("offline"):
        # No server connection — check cache
        cache = _read_cache()
        if cache and cache.get("key") == key and cache.get("hwid") == hwid:
            age = time.time() - cache.get("validated_at", 0)
            if age < GRACE_PERIOD_S:
                remaining = int((GRACE_PERIOD_S - age) / 86400)
                return LicenseStatus.OFFLINE_GRACE, f"Offline-Modus — {remaining} Tag(e) Gnadenfrist."
        return LicenseStatus.OFFLINE_FAIL, "Kein Internet und kein gültiger Cache."

    if not result.get("valid", False):
        msg = result.get("message", "Ungültiger Key.")
        return LicenseStatus.INVALID_KEY, msg

    if not result.get("hwid_ok", True):
        return LicenseStatus.HWID_MISMATCH, "Key ist an eine andere Hardware gebunden."

    expires = result.get("expires_at")
    if expires:
        try:
            from datetime import datetime
            exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            from datetime import timezone
            if exp_dt < datetime.now(timezone.utc):
                return LicenseStatus.EXPIRED, f"Key abgelaufen am {expires[:10]}."
        except Exception:
            pass

    # Cache success
    _write_cache({
        "key":          key,
        "hwid":         hwid,
        "validated_at": time.time(),
        "expires_at":   expires,
        "message":      result.get("message", ""),
    })
    return LicenseStatus.VALID, result.get("message", "Lizenz aktiv.")


def check_cached() -> tuple[str, str]:
    """
    Check if a valid cached license exists (no network call).
    Returns (status, message).
    """
    cache = _read_cache()
    if not cache:
        return LicenseStatus.NO_KEY, "Kein Key gefunden."

    hwid = _get_hwid()
    if cache.get("hwid") != hwid:
        return LicenseStatus.HWID_MISMATCH, "Hardware-ID stimmt nicht überein."

    age = time.time() - cache.get("validated_at", 0)
    if age >= GRACE_PERIOD_S:
        return LicenseStatus.OFFLINE_FAIL, "Cache abgelaufen — erneute Validierung erforderlich."

    expires = cache.get("expires_at")
    if expires:
        try:
            from datetime import datetime, timezone
            exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            if exp_dt < datetime.now(timezone.utc):
                _clear_cache()
                return LicenseStatus.EXPIRED, f"Key abgelaufen am {expires[:10]}."
        except Exception:
            pass

    return LicenseStatus.VALID, "Lizenz gültig (Cache)."


def get_hwid() -> str:
    """Return this machine's HWID for display / support."""
    return _get_hwid()


def revoke_local() -> None:
    """Remove cached license (used when user wants to transfer key)."""
    _clear_cache()
