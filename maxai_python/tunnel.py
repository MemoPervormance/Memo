"""Cloudflare Tunnel manager — auto-download cloudflared, parse tunnel URL."""
from __future__ import annotations
import logging
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger("maxai.tunnel")

_CF_RELEASE_URL = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
)
_TUNNEL_RE = re.compile(r"https://[a-z0-9\-]+\.trycloudflare\.com")


def _find_cloudflared() -> Optional[Path]:
    # 1. Next to this script / EXE
    local = Path(sys.executable).parent / "cloudflared.exe"
    if local.exists():
        return local
    local2 = Path(__file__).parent / "cloudflared.exe"
    if local2.exists():
        return local2
    # 2. PATH
    for d in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(d) / "cloudflared.exe"
        if candidate.exists():
            return candidate
    return None


def _download_cloudflared(dest: Path) -> bool:
    logger.info(f"Downloading cloudflared to {dest} …")
    try:
        urllib.request.urlretrieve(_CF_RELEASE_URL, str(dest))
        logger.info("cloudflared downloaded.")
        return True
    except Exception as exc:
        logger.error(f"cloudflared download failed: {exc}")
        return False


class TunnelManager:
    """Starts cloudflared tunnel, exposes parsed URL via .tunnel_url property."""

    def __init__(self, port: int) -> None:
        self._port = port
        self._proc: Optional[subprocess.Popen] = None
        self._url: Optional[str] = None
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None

    @property
    def tunnel_url(self) -> Optional[str]:
        with self._lock:
            return self._url

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True, name="tunnel")
        self._thread.start()

    def stop(self) -> None:
        with self._lock:
            if self._proc:
                try:
                    self._proc.terminate()
                except Exception:
                    pass
                self._proc = None
            self._url = None

    def _run(self) -> None:
        cf = _find_cloudflared()
        if cf is None:
            dest = Path(__file__).parent / "cloudflared.exe"
            if not _download_cloudflared(dest):
                logger.error("cloudflared unavailable — tunnel disabled.")
                return
            cf = dest

        cmd = [str(cf), "tunnel", "--url", f"http://127.0.0.1:{self._port}"]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            with self._lock:
                self._proc = proc

            for line in proc.stdout:  # type: ignore[union-attr]
                logger.debug(f"[cloudflared] {line.rstrip()}")
                m = _TUNNEL_RE.search(line)
                if m:
                    with self._lock:
                        self._url = m.group(0)
                    logger.info(f"Tunnel URL: {self._url}")

        except Exception as exc:
            logger.error(f"cloudflared process error: {exc}")
