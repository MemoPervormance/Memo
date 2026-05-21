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

# ── Ensure required directories exist before anything else ──
_ROOT = Path(__file__).parent
for _d in ("models", "profiles", "logs", "screenshots"):
    (_ROOT / _d).mkdir(exist_ok=True)

log_path = _ROOT / "logs" / "croixai.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("croixai.main")

# ── Import guard — show friendly error if deps missing ──────
def _check_deps():
    missing = []
    for pkg, mod in [
        ("fastapi",    "fastapi"),
        ("uvicorn",    "uvicorn"),
        ("pydantic",   "pydantic"),
        ("toml",       "toml"),
        ("numpy",      "numpy"),
        ("Pillow",     "PIL"),
    ]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("\n" + "="*55)
        print("  FEHLER: Fehlende Pakete:")
        for p in missing:
            print(f"    - {p}")
        print("\n  Lösung: INSTALL.bat ausführen")
        print("="*55 + "\n")
        sys.exit(1)

_check_deps()

from config import ConfigManager, ProfileManager
from assist_loop import AssistLoop, SharedState
from input_backends import create_backend, BACKEND_NAMES, BACKEND_LABELS
from web_server import create_app
from tunnel import TunnelManager
from discord_rpc import DiscordRPC

PORT = int(os.environ.get("CROIXAI_PORT", "17384"))

BANNER = r"""
  ██████╗██████╗  ██████╗ ██╗██╗  ██╗ █████╗ ██╗
 ██╔════╝██╔══██╗██╔═══██╗██║╚██╗██╔╝██╔══██╗██║
 ██║     ██████╔╝██║   ██║██║ ╚███╔╝ ███████║██║
 ██║     ██╔══██╗██║   ██║██║ ██╔██╗ ██╔══██║██║
 ╚██████╗██║  ██║╚██████╔╝██║██╔╝ ██╗██║  ██║██║
  ╚═════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝
"""


def _select_backend_interactive() -> str:
    print("\n" + "=" * 55)
    print("  Input Backend wählen")
    print("=" * 55)
    for i, name in enumerate(BACKEND_NAMES, 1):
        print(f"  [{i:2}]  {BACKEND_LABELS[name]}")
    print("=" * 55)
    raw = input("  Auswahl [1]: ").strip()
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(BACKEND_NAMES):
            return BACKEND_NAMES[idx]
    except ValueError:
        pass
    return BACKEND_NAMES[0]


def _parse_args():
    p = argparse.ArgumentParser(description="CroixAI Target Tracker")
    p.add_argument("--input",        choices=BACKEND_NAMES, default=None)
    p.add_argument("--port",         type=int, default=PORT)
    p.add_argument("--no-browser",   action="store_true")
    p.add_argument("--no-tunnel",    action="store_true")
    p.add_argument("--no-discord",   action="store_true")
    p.add_argument("--profile",      default=None)
    return p.parse_args()


def _scan_models() -> list[str]:
    """Return list of .onnx/.engine files found in models/ folder."""
    d = _ROOT / "models"
    return [f.name for f in d.iterdir() if f.suffix in (".onnx", ".engine")]


def main() -> None:
    args = _parse_args()
    port = args.port

    print(BANNER)
    print(f"  Version  : CroixAI v1.0")
    print(f"  Web-UI   : http://127.0.0.1:{port}")
    print(f"  Log      : {log_path}")

    # Show discovered models
    found_models = _scan_models()
    if found_models:
        print(f"\n  ✓ Models gefunden: {', '.join(found_models)}")
    else:
        print(f"\n  ⚠ Keine Models in models\\ — lege .onnx Datei dort ab.")

    logger.info("CroixAI starting…")

    cfg_mgr  = ConfigManager()
    cfg      = cfg_mgr.get()
    prof_mgr = ProfileManager()

    if args.profile:
        prof_mgr.switch(args.profile)

    # Auto-load first found model if config has no model set
    if not cfg.detection.model_path and found_models:
        first = str(_ROOT / "models" / found_models[0])
        cfg_mgr.update({"detection": {"model_path": first}})
        print(f"  → Model automatisch gesetzt: {found_models[0]}")

    # Input backend — selection saved to config so UI can change it later
    backend_name = args.input or cfg.input.backend or _select_backend_interactive()
    # Save selection to config so web UI reflects current backend
    cfg_mgr.update({"input": {"backend": backend_name}})
    logger.info(f"Input backend: {backend_name}")
    print(f"\n  Backend: {BACKEND_LABELS.get(backend_name, backend_name)}")

    state = SharedState(
        input_backend_name=backend_name,
        capture_backend_name=cfg.capture.backend,
        active_profile=prof_mgr.active_name,
    )

    def loop_factory() -> AssistLoop:
        # Re-read backend from config so UI changes take effect on loop restart
        current_cfg = cfg_mgr.get()
        cur_backend_name = current_cfg.input.backend or backend_name
        try:
            cur_backend = create_backend(cur_backend_name, current_cfg)
        except Exception as exc:
            logger.error(f"Backend init failed ({cur_backend_name}): {exc}")
            cur_backend = create_backend("relative_mouse", current_cfg)
            cur_backend_name = "relative_mouse"
        state.set(input_backend_name=cur_backend_name)
        return AssistLoop(state, cfg_mgr, prof_mgr, cur_backend, cur_backend_name)

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
        try:
            discord = DiscordRPC()
            discord.start()
        except Exception:
            pass

    _stop = threading.Event()

    def _shutdown(*_):
        logger.info("Shutdown.")
        _stop.set()
        if discord:
            discord.stop()
        if tunnel:
            tunnel.stop()

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

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
            import time; time.sleep(1.5)
            webbrowser.open(f"http://127.0.0.1:{port}")
        threading.Thread(target=_open, daemon=True).start()

    print(f"\n  Hotkeys: RMB=Aim | F6=Toggle | Pause=Pause | Insert=Overlay | F12=Exit")
    print(f"  Browser öffnet automatisch — oder manuell: http://127.0.0.1:{port}\n")

    try:
        import uvicorn  # type: ignore[import]
    except ImportError:
        print("\n  [FEHLER] uvicorn nicht installiert — INSTALL.bat ausführen!\n")
        sys.exit(1)

    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    )
    threading.Thread(target=server.run, daemon=True, name="uvicorn").start()
    _stop.wait()
    server.should_exit = True
    logger.info("CroixAI exiting.")


if __name__ == "__main__":
    main()
