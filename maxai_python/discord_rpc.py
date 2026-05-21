"""Discord Rich Presence via pypresence."""
from __future__ import annotations
import logging
import threading
import time
from typing import Optional

logger = logging.getLogger("maxai.discord")

APP_ID = "1491143865812516984"
_ASSET_KEY = "maxai_logo"


class DiscordRPC:
    """Manages Discord Rich Presence in a background thread."""

    def __init__(self) -> None:
        self._rpc = None
        self._connected = False
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_flag = False

    def start(self) -> None:
        self._stop_flag = False
        self._thread = threading.Thread(target=self._run, daemon=True, name="discord-rpc")
        self._thread.start()

    def stop(self) -> None:
        self._stop_flag = True
        with self._lock:
            if self._rpc and self._connected:
                try:
                    self._rpc.clear()
                    self._rpc.close()
                except Exception:
                    pass
            self._connected = False
            self._rpc = None

    def _run(self) -> None:
        try:
            from pypresence import Presence  # type: ignore[import]
        except ImportError:
            logger.warning("pypresence not installed — Discord RPC disabled.")
            return

        while not self._stop_flag:
            with self._lock:
                if not self._connected:
                    try:
                        rpc = Presence(APP_ID)
                        rpc.connect()
                        self._rpc = rpc
                        self._connected = True
                        logger.info("Discord RPC connected.")
                    except Exception as exc:
                        logger.debug(f"Discord RPC connect failed: {exc}")
                        self._rpc = None

                if self._connected and self._rpc:
                    try:
                        self._rpc.update(
                            details="MAX-AI",
                            state="Spielt MAX-AI",
                            large_image=_ASSET_KEY,
                            large_text="MAX-AI",
                        )
                    except Exception as exc:
                        logger.debug(f"Discord RPC update failed: {exc}")
                        self._connected = False
                        self._rpc = None

            time.sleep(15)
