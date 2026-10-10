"""FastAPI app factory — entry point."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import (
    auth, campaigns, dashboard, editing, export, health, plans,
    profile, regenerate, reports, runs, validation,
)
from app.api.errors import api_error_handler, unhandled_exception_handler
from app.config import get_settings
from app.db.session import init_db

# Ensure INFO-level logging so one-time codes print to console in dev
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="AI Social Media Manager",
        version="0.8.0",
        docs_url="/docs",
        redoc_url=None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handlers
    app.add_exception_handler(StarletteHTTPException, api_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Startup: create tables
    @app.on_event("startup")
    def _startup():
        init_db()

    # Routes — all under /api
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router)
    app.include_router(profile.router)
    app.include_router(runs.router, prefix="/api")
    app.include_router(plans.router, prefix="/api")
    app.include_router(campaigns.router)
    app.include_router(validation.router, prefix="/api")
    app.include_router(editing.router, prefix="/api")
    app.include_router(regenerate.router, prefix="/api")
    app.include_router(export.router, prefix="/api")
    app.include_router(reports.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")

    return app


app = create_app()
