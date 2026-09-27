"""FastAPI application factory for the platform API."""

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from agency.api.approvals import build_router as build_approvals_router
from agency.api.audit import build_router as build_audit_router
from agency.api.auth import build_router as build_auth_router
from agency.api.build import build_router as build_build_router
from agency.api.content import build_router as build_content_router
from agency.api.deploy import build_router as build_deploy_router
from agency.api.dashboard import build_router as build_dashboard_router
from agency.api.design import build_router as build_design_router
from agency.api.intake import build_router as build_intake_router
from agency.api.leads import build_router as build_leads_router
from agency.api.publish import build_router as build_publish_router
from agency.api.research import build_router as build_research_router
from agency.db.session import create_all, create_session_factory
from agency.services.csrf_service import CSRF_COOKIE, CSRF_HEADER, valid_csrf_token


def create_app(database_url: str = "sqlite:///agency.db") -> FastAPI:
    session_factory: sessionmaker = create_session_factory(database_url)
    create_all(database_url)
    app = FastAPI(title="AI Web Agency API", version="0.1.0")
    origins = [item.strip() for item in os.getenv("AGENCY_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if item.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["*", CSRF_HEADER],
    )

    @app.middleware("http")
    async def csrf_protection(request: Request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            session_cookie = request.cookies.get("agency_session")
            exempt = {"/v1/auth/bootstrap", "/v1/auth/login"}
            if session_cookie and request.url.path not in exempt:
                if not valid_csrf_token(
                    request.cookies.get(CSRF_COOKIE),
                    request.headers.get(CSRF_HEADER),
                ):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF token required"},
                    )
        return await call_next(request)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(build_auth_router(session_factory))
    app.include_router(build_audit_router(session_factory))
    app.include_router(build_intake_router(session_factory))
    app.include_router(build_approvals_router(session_factory))
    app.include_router(build_research_router(session_factory))
    app.include_router(build_content_router(session_factory))
    app.include_router(build_design_router(session_factory))
    app.include_router(build_build_router(session_factory))
    app.include_router(build_publish_router(session_factory))
    app.include_router(build_deploy_router(session_factory))
    app.include_router(build_leads_router(session_factory))
    app.include_router(build_dashboard_router(session_factory))
    return app


app = create_app()
