"""CroixAI — entry point. Backend selection, web server, assist loop."""
from __future__ import annotations
import argparse
import logging
import os
import signal
import sys
import threading
import webbrowser
from pathlib import Path

log_path = Path(__file__).parent / "croixai.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("croixai.main")

from config import ConfigManager, ProfileManager
from assist_loop import AssistLoop, SharedState
from input_backends import create_backend, BACKEND_NAMES, BACKEND_LABELS
from web_server import create_app
from tunnel import TunnelManager
from discord_rpc import DiscordRPC

PORT = int(os.environ.get("MAXAI_PORT", "17384"))


# ---------------------------------------------------------------------------
# Startup menu
# ---------------------------------------------------------------------------

def _select_backend_interactive() -> str:
    print("\n" + "=" * 58)
    print("  CroixAI  —  Input Backend")
    print("=" * 58)
    for i, name in enumerate(BACKEND_NAMES, 1):
        print(f"  [{i}] {BACKEND_LABELS[name]}")
    print("=" * 58)
    raw = input(f"Auswahl [1]: ").strip()
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(BACKEND_NAMES):
            return BACKEND_NAMES[idx]
    except ValueError:
        pass
    return "relative_mouse"


def _parse_args():
    p = argparse.ArgumentParser(description="CroixAI Target Tracker")
    p.add_argument("--input",   choices=BACKEND_NAMES, default=None)
    p.add_argument("--port",    type=int, default=PORT)
    p.add_argument("--no-browser",  action="store_true")
    p.add_argument("--no-tunnel",   action="store_true")
    p.add_argument("--no-discord",  action="store_true")
    p.add_argument("--profile",     default=None, help="Start with named game profile")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args   = _parse_args()
    port   = args.port

    logger.info("CroixAI starting…")

    cfg_mgr  = ConfigManager()
    cfg      = cfg_mgr.get()
    prof_mgr = ProfileManager()

    if args.profile:
        prof_mgr.switch(args.profile)

    # Input backend
    backend_name = args.input or _select_backend_interactive()
    logger.info(f"Input backend: {backend_name}")
    print(f"\n  Backend: {BACKEND_LABELS.get(backend_name, backend_name)}\n")

    try:
        backend = create_backend(backend_name, cfg)
    except Exception as exc:
        logger.error(f"Backend init failed: {exc}")
        print(f"\n[ERROR] {exc}\n")
        sys.exit(1)

    # Shared state
    state = SharedState(
        input_backend_name=backend_name,
        capture_backend_name=cfg.capture.backend,
        active_profile=prof_mgr.active_name,
    )

    # Loop factory
    def loop_factory() -> AssistLoop:
        return AssistLoop(state, cfg_mgr, prof_mgr, backend, backend_name)

    # Tunnel
    tunnel: TunnelManager | None = None
    if not args.no_tunnel:
        tunnel = TunnelManager(port)
        tunnel.start()

    def _update_tunnel_url():
        import time
        while True:
            if tunnel:
                state.tunnel_url = tunnel.tunnel_url
            time.sleep(5)

    threading.Thread(target=_update_tunnel_url, daemon=True, name="tunnel-url").start()

    # Discord
    discord: DiscordRPC | None = None
    if not args.no_discord and cfg.info.discord_rpc:
        discord = DiscordRPC()
        discord.start()

    _stop = threading.Event()

    def _shutdown(*_):
        logger.info("Shutdown.")
        _stop.set()
        if discord:
            discord.stop()
        if tunnel:
            tunnel.stop()
        backend.release_all()

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Web app
    app = create_app(
        state=state,
        config_mgr=cfg_mgr,
        profile_mgr=prof_mgr,
        loop_factory=loop_factory,
        tunnel_stop_fn=lambda: tunnel.stop() if tunnel else None,
        app_stop_fn=_stop.set,
    )

    if not args.no_browser:
        def _open():
            import time; time.sleep(1.2)
            webbrowser.open(f"http://127.0.0.1:{port}")
        threading.Thread(target=_open, daemon=True).start()

    print(f"  Web-UI:  http://127.0.0.1:{port}")
    print(f"  Log:     {log_path}")
    print(f"  F12=Exit | F6=Toggle | F4=Reload | Pause=Pause | Insert=Overlay\n")

    import uvicorn  # type: ignore[import]
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    threading.Thread(target=server.run, daemon=True, name="uvicorn").start()
    _stop.wait()
    server.should_exit = True
    logger.info("CroixAI exiting.")


if __name__ == "__main__":
    main()
