"""Discord / Telegram webhook dispatcher + webhook_logs writer."""
from __future__ import annotations
import json
import logging
import os
import threading
from datetime import datetime
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

logger = logging.getLogger("catalyst.webhook")

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
TELEGRAM_BOT_TOKEN  = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID    = os.environ.get("TELEGRAM_CHAT_ID", "")


def _write_log(db: Session, event_type: str, payload: str, status_code: int) -> None:
    from models import WebhookLog
    log = WebhookLog(
        event_type=event_type,
        payload=payload,
        status_code=status_code,
    )
    db.add(log)
    db.commit()


def _send_discord(event_type: str, data: dict, db: Optional[Session] = None) -> None:
    if not DISCORD_WEBHOOK_URL:
        return
    payload = {
        "embeds": [{
            "title":       f"[Catalyst] {event_type}",
            "description": "\n".join(f"**{k}**: {v}" for k, v in data.items()),
            "color":       0x7289DA,
            "timestamp":   datetime.utcnow().isoformat(),
        }]
    }
    raw = json.dumps(payload)
    try:
        r = httpx.post(DISCORD_WEBHOOK_URL, content=raw,
                       headers={"Content-Type": "application/json"}, timeout=5)
        code = r.status_code
    except Exception as exc:
        logger.warning(f"Discord webhook failed: {exc}")
        code = 0
    if db:
        _write_log(db, event_type, raw, code)


def _send_telegram(event_type: str, data: dict, db: Optional[Session] = None) -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    text = f"*[Catalyst] {event_type}*\n" + "\n".join(f"{k}: `{v}`" for k, v in data.items())
    url  = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    raw  = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
    try:
        r = httpx.post(url, content=raw,
                       headers={"Content-Type": "application/json"}, timeout=5)
        code = r.status_code
    except Exception as exc:
        logger.warning(f"Telegram webhook failed: {exc}")
        code = 0
    if db:
        _write_log(db, f"telegram:{event_type}", raw, code)


def fire(event_type: str, data: dict[str, Any], db: Optional[Session] = None) -> None:
    """Fire webhook in background thread — non-blocking."""
    def _run():
        _send_discord(event_type, data, db)
        _send_telegram(event_type, data, db)

    threading.Thread(target=_run, daemon=True).start()
