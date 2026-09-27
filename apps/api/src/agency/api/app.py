"""FastAPI application factory for the platform API."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from agency.api.approvals import build_router as build_approvals_router
from agency.api.build import build_router as build_build_router
from agency.api.content import build_router as build_content_router
from agency.api.deploy import build_router as build_deploy_router
from agency.api.design import build_router as build_design_router
from agency.api.intake import build_router as build_intake_router
from agency.api.leads import build_router as build_leads_router
from agency.api.publish import build_router as build_publish_router
from agency.api.research import build_router as build_research_router
from agency.db.session import create_all, create_session_factory


def create_app(database_url: str = "sqlite:///agency.db") -> FastAPI:
    session_factory: sessionmaker = create_session_factory(database_url)
    create_all(database_url)
    app = FastAPI(title="AI Web Agency API", version="0.1.0")
    origins = [item.strip() for item in os.getenv("AGENCY_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if item.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(build_intake_router(session_factory))
    app.include_router(build_approvals_router(session_factory))
    app.include_router(build_research_router(session_factory))
    app.include_router(build_content_router(session_factory))
    app.include_router(build_design_router(session_factory))
    app.include_router(build_build_router(session_factory))
    app.include_router(build_publish_router(session_factory))
    app.include_router(build_deploy_router(session_factory))
    app.include_router(build_leads_router(session_factory))
    return app


app = create_app()
