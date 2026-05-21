"""Catalyst Auth System — FastAPI application entry point."""
from __future__ import annotations
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import engine, Base
import models  # noqa: F401  — register all ORM models

from routers import (
    auth, users, hwid, licenses, sessions,
    notifications, announcements, api_tokens, settings, subscriptions,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables if they don't exist (use Alembic for production migrations)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Catalyst Auth System",
    version="1.0.0",
    description="Full-control authentication & licensing backend",
    lifespan=lifespan,
)

# CORS — adjust origins for production
_CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(hwid.router)
app.include_router(licenses.router)
app.include_router(sessions.router)
app.include_router(notifications.router)
app.include_router(announcements.router)
app.include_router(api_tokens.router)
app.include_router(settings.router)
app.include_router(subscriptions.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "catalyst-auth"}


@app.get("/")
def root():
    return JSONResponse({
        "service": "Catalyst Auth System",
        "docs":    "/docs",
        "health":  "/health",
    })
