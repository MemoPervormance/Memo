"""FastAPI web server — REST API routes matching Rust axum endpoints."""
from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from assist_loop import AssistLoop, SharedState
from config import ConfigManager

logger = logging.getLogger("maxai.web")

_HTML_PATH = Path(__file__).parent / "static" / "web_ui.html"


def create_app(
    state: SharedState,
    config_mgr: ConfigManager,
    loop_factory,           # callable () -> AssistLoop
    tunnel_stop_fn=None,    # callable to kill tunnel
    app_stop_fn=None,       # callable to exit app
) -> FastAPI:

    app = FastAPI(title="MAX-AI", docs_url=None, redoc_url=None)

    # Serve static files (for any extra assets)
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    _loop_ref: list[Optional[AssistLoop]] = [None]

    # ------------------------------------------------------------------
    # GET /  — Web UI HTML
    # ------------------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    async def index():
        if _HTML_PATH.exists():
            return HTMLResponse(_HTML_PATH.read_text(encoding="utf-8"))
        return HTMLResponse("<h1>MAX-AI</h1><p>web_ui.html not found.</p>")

    # ------------------------------------------------------------------
    # GET /x/s  — Status JSON
    # ------------------------------------------------------------------
    @app.get("/x/s")
    async def status():
        snap = state.snapshot()
        snap["tunnel_url"] = state.tunnel_url
        return JSONResponse(snap)

    # ------------------------------------------------------------------
    # GET /x/c  — Get config
    # POST /x/c — Partial update config
    # ------------------------------------------------------------------
    @app.get("/x/c")
    async def config_get():
        return JSONResponse(config_mgr.get().model_dump())

    class _AnyBody(BaseModel):
        model_config = {"extra": "allow"}

    @app.post("/x/c")
    async def config_set(body: dict):
        updated = config_mgr.update(body)
        return JSONResponse(updated.model_dump())

    # ------------------------------------------------------------------
    # POST /x/r  — Start assist loop
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
    # POST /x/v  — Save config to TOML
    # ------------------------------------------------------------------
    @app.post("/x/v")
    async def save_config():
        config_mgr.save()
        return JSONResponse({"ok": True, "path": str(config_mgr.path)})

    # ------------------------------------------------------------------
    # POST /x/k  — Kill app + tunnel
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

    return app
