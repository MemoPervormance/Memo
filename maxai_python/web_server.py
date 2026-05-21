"""FastAPI web server — REST API including game profile, setup wizard, and presets routes."""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from assist_loop import AssistLoop, SharedState
from config import ConfigManager, ProfileManager
from setup_wizard import check_all, check_driver, install_driver, get_install_progress, SETUP_GUIDE
from game_presets import GAME_PRESETS, get_preset, apply_preset
from model_registry import list_models, get_model_info, get_models_for_game, get_download_status

logger = logging.getLogger("croixai.web")
_HTML_PATH = Path(__file__).parent / "static" / "web_ui.html"


def create_app(
    state: SharedState,
    config_mgr: ConfigManager,
    profile_mgr: ProfileManager,
    loop_factory,
    tunnel_stop_fn=None,
    app_stop_fn=None,
) -> FastAPI:

    app = FastAPI(title="CroixAI", docs_url=None, redoc_url=None)

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    _loop_ref: list[Optional[AssistLoop]] = [None]

    # ------------------------------------------------------------------
    # GET /
    # ------------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    async def index():
        if _HTML_PATH.exists():
            return HTMLResponse(_HTML_PATH.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>CroixAI</h1><p>web_ui.html not found.</p>")

    # ------------------------------------------------------------------
    # GET /x/s  — Status
    # ------------------------------------------------------------------
    @app.get("/x/s")
    async def status():
        snap = state.snapshot()
        snap["tunnel_url"] = state.tunnel_url
        return JSONResponse(snap)

    # ------------------------------------------------------------------
    # GET|POST /x/c  — Config
    # ------------------------------------------------------------------
    @app.get("/x/c")
    async def config_get():
        return JSONResponse(config_mgr.get().model_dump())

    @app.post("/x/c")
    async def config_set(body: dict):
        updated = config_mgr.update(body)
        return JSONResponse(updated.model_dump())

    # ------------------------------------------------------------------
    # POST /x/r  — Start loop
    # ------------------------------------------------------------------
    @app.post("/x/r")
    async def start_loop():
        if _loop_ref[0] is None or not state.running:
            _loop_ref[0] = loop_factory()
            started = _loop_ref[0].start()
            return JSONResponse({"ok": started})
        return JSONResponse({"ok": False, "reason": "already running"})

    # ------------------------------------------------------------------
    # POST /x/p  — Stop loop
    # ------------------------------------------------------------------
    @app.post("/x/p")
    async def stop_loop():
        if _loop_ref[0]:
            _loop_ref[0].stop()
        return JSONResponse({"ok": True})

    # ------------------------------------------------------------------
    # POST /x/t  — Toggle enabled
    # ------------------------------------------------------------------
    @app.post("/x/t")
    async def toggle():
        state.set(enabled=not state.enabled)
        return JSONResponse({"enabled": state.enabled})

    # ------------------------------------------------------------------
    # POST /x/v  — Save config
    # ------------------------------------------------------------------
    @app.post("/x/v")
    async def save_config():
        config_mgr.save()
        return JSONResponse({"ok": True, "path": str(config_mgr.path)})

    # ------------------------------------------------------------------
    # POST /x/k  — Kill
    # ------------------------------------------------------------------
    @app.post("/x/k")
    async def kill():
        if _loop_ref[0]:
            _loop_ref[0].stop()
        if tunnel_stop_fn:
            tunnel_stop_fn()
        if app_stop_fn:
            app_stop_fn()
        return JSONResponse({"ok": True})

    # ------------------------------------------------------------------
    # Game Profiles
    # ------------------------------------------------------------------
    @app.get("/x/profiles")
    async def list_profiles():
        return JSONResponse({
            "profiles": profile_mgr.list_profiles(),
            "active":   profile_mgr.active_name,
        })

    @app.post("/x/profiles/{name}")
    async def create_or_save_profile(name: str, body: dict = None):
        if body:
            from config import GameProfileConfig
            body["name"] = name
            try:
                p = GameProfileConfig.model_validate(body)
                profile_mgr.save_profile(p)
            except Exception as exc:
                raise HTTPException(400, str(exc))
        else:
            profile_mgr.create(name)
        p = profile_mgr.get(name)
        return JSONResponse(p.model_dump() if p else {})

    @app.get("/x/profiles/{name}")
    async def get_profile(name: str):
        p = profile_mgr.get(name)
        if not p:
            raise HTTPException(404, f"Profile '{name}' not found")
        return JSONResponse(p.model_dump())

    @app.post("/x/profiles/{name}/switch")
    async def switch_profile(name: str):
        ok = profile_mgr.switch(name)
        if not ok:
            raise HTTPException(404, f"Profile '{name}' not found")
        state.set(active_profile=name)
        return JSONResponse({"ok": True, "active": name})

    @app.delete("/x/profiles/{name}")
    async def delete_profile(name: str):
        ok = profile_mgr.delete(name)
        if not ok:
            raise HTTPException(400, "Cannot delete — profile not found or is 'default'")
        return JSONResponse({"ok": True})

    # ------------------------------------------------------------------
    # Setup Wizard
    # ------------------------------------------------------------------
    @app.get("/x/setup/check")
    async def setup_check():
        return JSONResponse({"drivers": check_all(), "guide": SETUP_GUIDE})

    @app.get("/x/setup/check/{driver_id}")
    async def setup_check_one(driver_id: str):
        return JSONResponse(check_driver(driver_id))

    @app.post("/x/setup/install/{driver_id}")
    async def setup_install(driver_id: str):
        current = get_install_progress(driver_id)
        if current.startswith("starting") or current == "Installing":
            return JSONResponse({"ok": False, "reason": "already installing"})
        install_driver(driver_id)
        return JSONResponse({"ok": True, "status": "started"})

    @app.get("/x/setup/progress/{driver_id}")
    async def setup_progress(driver_id: str):
        return JSONResponse({"status": get_install_progress(driver_id)})

    # ------------------------------------------------------------------
    # Game Presets
    # ------------------------------------------------------------------
    @app.get("/x/presets")
    async def list_presets():
        safe = [
            {k: v for k, v in p.items() if k != "config"}
            for p in GAME_PRESETS
        ]
        return JSONResponse({"presets": safe})

    @app.get("/x/presets/{game_id}")
    async def get_preset_detail(game_id: str):
        p = get_preset(game_id)
        if not p:
            raise HTTPException(404, f"Preset '{game_id}' not found")
        return JSONResponse(p)

    @app.post("/x/presets/{game_id}/apply")
    async def apply_game_preset(game_id: str):
        ok = apply_preset(game_id, config_mgr)
        if not ok:
            raise HTTPException(404, f"Preset '{game_id}' not found")
        return JSONResponse({"ok": True, "applied": game_id})

    # ------------------------------------------------------------------
    # Model Registry
    # ------------------------------------------------------------------
    @app.get("/x/models")
    async def list_model_registry():
        models_dir = Path(__file__).parent / "models"
        models_dir.mkdir(exist_ok=True)
        download_status = get_download_status(models_dir)
        models = []
        for m in list_models():
            entry = {k: v for k, v in m.items() if k != "recommended_for"}
            entry["on_disk"] = download_status.get(m["name"], False)
            models.append(entry)
        return JSONResponse({"models": models})

    @app.get("/x/models/{model_name}")
    async def get_model_detail(model_name: str):
        info = get_model_info(model_name)
        if not info:
            raise HTTPException(404, f"Model '{model_name}' not found")
        models_dir = Path(__file__).parent / "models"
        on_disk = (models_dir / info["filename"]).exists()
        return JSONResponse({**info, "on_disk": on_disk})

    @app.get("/x/models/for/{game_id}")
    async def models_for_game(game_id: str):
        models_dir = Path(__file__).parent / "models"
        result = []
        for m in get_models_for_game(game_id):
            on_disk = (models_dir / m["filename"]).exists()
            result.append({**m, "on_disk": on_disk})
        return JSONResponse({"models": result, "game_id": game_id})

    @app.post("/x/models/{model_name}/use")
    async def use_model(model_name: str):
        info = get_model_info(model_name)
        if not info:
            raise HTTPException(404, f"Model '{model_name}' not found")
        models_dir = Path(__file__).parent / "models"
        model_path = models_dir / info["filename"]
        if not model_path.exists():
            raise HTTPException(400, f"Model file not found: {info['filename']}. Train it first.")
        updated = config_mgr.update({
            "detection": {
                "model_path":             str(model_path),
                "confidence_threshold":   info["confidence"],
                "nms_threshold":          info["nms"],
                "blob_size":              info["blob_size"],
                "use_tensorrt":           False,
            }
        })
        return JSONResponse({"ok": True, "model": model_name, "path": str(model_path)})

    # ------------------------------------------------------------------
    # Model file scanner — lists all .onnx/.engine in models/ folder
    # ------------------------------------------------------------------
    @app.get("/x/models/scan")
    async def scan_model_files():
        models_dir = Path(__file__).parent / "models"
        models_dir.mkdir(exist_ok=True)
        files = []
        for f in sorted(models_dir.iterdir()):
            if f.suffix in (".onnx", ".engine"):
                files.append({
                    "filename": f.name,
                    "path":     str(f),
                    "size_mb":  round(f.stat().st_size / 1_048_576, 1),
                    "type":     "tensorrt" if f.suffix == ".engine" else "onnx",
                })
        return JSONResponse({"files": files, "folder": str(models_dir)})

    @app.post("/x/models/load-file")
    async def load_model_file(body: dict):
        filename = body.get("filename", "")
        models_dir = Path(__file__).parent / "models"
        path = models_dir / filename
        if not path.exists():
            raise HTTPException(404, f"Datei nicht gefunden: {filename}")
        config_mgr.update({
            "detection": {
                "model_path":   str(path),
                "use_tensorrt": path.suffix == ".engine",
            }
        })
        return JSONResponse({"ok": True, "path": str(path)})

    return app
