"""FastAPI web server — REST API including game profile routes."""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from assist_loop import AssistLoop, SharedState
from config import ConfigManager, ProfileManager

logger = logging.getLogger("maxai.web")
_HTML_PATH = Path(__file__).parent / "static" / "web_ui.html"


def create_app(
    state: SharedState,
    config_mgr: ConfigManager,
    profile_mgr: ProfileManager,
    loop_factory,
    tunnel_stop_fn=None,
    app_stop_fn=None,
) -> FastAPI:

    app = FastAPI(title="MAX-AI", docs_url=None, redoc_url=None)

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
        return HTMLResponse("<h1>MAX-AI</h1><p>web_ui.html not found.</p>")

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

    return app
