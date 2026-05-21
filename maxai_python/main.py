"""MAX-AI — entry point. Startup menu, backend selection, web server + assist loop."""
from __future__ import annotations
import argparse
import logging
import os
import signal
import sys
import threading
import webbrowser
from pathlib import Path

# Configure logging before any imports that set up sub-loggers
log_path = Path(__file__).parent / "maxai.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("maxai.main")

from config import ConfigManager
from assist_loop import AssistLoop, SharedState
from input_backends import create_backend
from web_server import create_app
from tunnel import TunnelManager
from discord_rpc import DiscordRPC

PORT = int(os.environ.get("MAXAI_PORT", "17384"))

# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------

_BACKENDS = {
    "1": "relative_mouse",
    "2": "virtual_gamepad",
    "3": "kernel_driver",
}
_BACKEND_LABELS = {
    "relative_mouse":  "Relative Mouse (SendInput — kein Treiber nötig)",
    "virtual_gamepad": "Virtual Gamepad (ViGEmBus Xbox360)",
    "kernel_driver":   "Kernel Driver (IOCTL — eigener Treiber erforderlich)",
}


def _select_backend_interactive() -> str:
    print("\n" + "="*52)
    print("  MAX-AI  —  Input Backend Auswahl")
    print("="*52)
    for k, name in _BACKENDS.items():
        print(f"  [{k}] {_BACKEND_LABELS[name]}")
    print("="*52)
    choice = input("Auswahl [1]: ").strip() or "1"
    return _BACKENDS.get(choice, "relative_mouse")


def _parse_args():
    p = argparse.ArgumentParser(description="MAX-AI Target Tracker")
    p.add_argument(
        "--input",
        choices=["relative_mouse", "virtual_gamepad", "kernel_driver"],
        default=None,
        help="Input backend (skips interactive menu)",
    )
    p.add_argument("--port", type=int, default=PORT, help="Web server port")
    p.add_argument("--no-browser", action="store_true", help="Don't open browser on start")
    p.add_argument("--no-tunnel",  action="store_true", help="Skip cloudflare tunnel")
    p.add_argument("--no-discord", action="store_true", help="Skip Discord RPC")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()
    port = args.port

    logger.info("MAX-AI starting…")

    # Config
    cfg_mgr = ConfigManager()
    cfg     = cfg_mgr.get()

    # Backend selection
    if args.input:
        backend_name = args.input
    else:
        backend_name = _select_backend_interactive()

    logger.info(f"Input backend: {backend_name}")
    print(f"\n  Backend: {_BACKEND_LABELS.get(backend_name, backend_name)}\n")

    try:
        backend = create_backend(backend_name, cfg)
    except Exception as exc:
        logger.error(f"Backend init failed: {exc}")
        print(f"\n[ERROR] Backend konnte nicht initialisiert werden:\n{exc}\n")
        sys.exit(1)

    # Shared state
    state = SharedState(input_backend_name=backend_name)

    # Assist loop factory
    def loop_factory() -> AssistLoop:
        return AssistLoop(state, cfg_mgr, backend, backend_name)

    # Tunnel
    tunnel: TunnelManager | None = None
    if not args.no_tunnel:
        tunnel = TunnelManager(port)
        tunnel.start()

    def _get_tunnel_url():
        return tunnel.tunnel_url if tunnel else None

    # Patch state.tunnel_url property dynamically via polling thread
    def _tunnel_url_updater():
        import time
        while True:
            if tunnel:
                state.tunnel_url = tunnel.tunnel_url
            time.sleep(5)

    threading.Thread(target=_tunnel_url_updater, daemon=True, name="tunnel-updater").start()

    # Discord RPC
    discord: DiscordRPC | None = None
    if not args.no_discord and cfg.info.discord_rpc:
        discord = DiscordRPC()
        discord.start()

    # Graceful shutdown
    _stop = threading.Event()

    def _shutdown(*_):
        logger.info("Shutdown signal received.")
        _stop.set()
        if discord:
            discord.stop()
        if tunnel:
            tunnel.stop()
        backend.release_all()

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    def _app_stop():
        _stop.set()

    def _tunnel_stop():
        if tunnel:
            tunnel.stop()

    # Web app
    app = create_app(
        state=state,
        config_mgr=cfg_mgr,
        loop_factory=loop_factory,
        tunnel_stop_fn=_tunnel_stop,
        app_stop_fn=_app_stop,
    )

    # Open browser
    if not args.no_browser:
        def _open():
            import time; time.sleep(1.2)
            webbrowser.open(f"http://127.0.0.1:{port}")
        threading.Thread(target=_open, daemon=True, name="browser").start()

    print(f"  Web-UI: http://127.0.0.1:{port}")
    print(f"  Log:    {log_path}")
    print(f"  F12     = Loop beenden  |  F6 = Assist Toggle  |  Ctrl+C = Beenden\n")

    # Start uvicorn
    import uvicorn  # type: ignore[import]
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port,
        log_level="warning", loop="asyncio",
    )
    server = uvicorn.Server(config)

    # Run server in thread so we can watch _stop event
    server_thread = threading.Thread(target=server.run, daemon=True, name="uvicorn")
    server_thread.start()

    _stop.wait()
    server.should_exit = True
    logger.info("MAX-AI exiting.")


if __name__ == "__main__":
    main()
