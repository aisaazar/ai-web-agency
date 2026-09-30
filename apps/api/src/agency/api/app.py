"""FastAPI application factory for the platform API."""

import os
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from agency.services.error_reporting import report_exception

from agency.api.agent import build_router as build_agent_router
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
from agency.services.rate_limit_service import RateLimitError, enforce


def create_app(database_url: str | None = None) -> FastAPI:
    environment = os.getenv("AGENCY_ENV", "development").strip().lower()
    configured_database_url = os.getenv("AGENCY_DATABASE_URL", "").strip()
    if database_url is None:
        if environment == "production" and not configured_database_url:
            raise RuntimeError("production requires AGENCY_DATABASE_URL")
        database_url = configured_database_url or "sqlite:///agency.db"
    if not database_url.strip():
        raise RuntimeError("database URL must not be empty")
    session_factory: sessionmaker = create_session_factory(database_url)
    create_all(database_url)
    app = FastAPI(title="AI Web Agency API", version="0.1.0")
    origins = [item.strip() for item in os.getenv("AGENCY_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if item.strip()]
    if environment == "production":
        if not origins or any(origin == "*" or not origin.lower().startswith("https://") for origin in origins):
            raise RuntimeError("production requires explicit HTTPS AGENCY_ALLOWED_ORIGINS")
        secure_cookie = os.getenv("AGENCY_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}
        if not secure_cookie:
            raise RuntimeError("production requires AGENCY_COOKIE_SECURE=true")
        if not os.getenv("AGENCY_TURNSTILE_SECRET", "").strip():
            raise RuntimeError("production requires AGENCY_TURNSTILE_SECRET")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["*", CSRF_HEADER],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid4()))
        report_exception(
            exc,
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "internal server error", "request_id": request_id},
            headers={"X-Request-ID": request_id, "Cache-Control": "no-store"},
        )

    @app.middleware("http")
    async def public_rate_limit(request: Request, call_next):
        path = request.url.path
        if request.method == "POST" and (path == "/v1/leads" or path.startswith("/v1/agent/")):
            host = request.client.host if request.client else "unknown"
            key = f"{host}:{path.split('/')[1:4]}"
            try:
                if path == "/v1/leads":
                    enforce(key, limit=20, window_seconds=60)
                else:
                    enforce(key, limit=60, window_seconds=60)
            except RateLimitError:
                return JSONResponse(status_code=429, content={"detail": "rate limit exceeded"}, headers={"Retry-After": "60"})
        return await call_next(request)

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

    app.include_router(build_agent_router(session_factory))
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
