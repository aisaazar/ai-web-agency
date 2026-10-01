"""Deployment endpoints."""
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, sessionmaker

from agency.api.auth_dependencies import require_role_or_legacy
from agency.api.dependencies import get_db
from agency.providers.deployment_registry import get_deployment_provider
from agency.services.deploy_service import (
    DeployError,
    attach_domain,
    create_preview,
    deployment_logs,
    publish_site,
    rollback_site,
)


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    site_version_id: UUID
    provider: str = Field(default="local_static", min_length=1, max_length=64)


class PublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    site_version_id: UUID


class RollbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    build_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class DomainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    fqdn: str = Field(min_length=1, max_length=253)


class DeploymentLogsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    deploy_id: UUID


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/deploys", tags=["deployments"])
    db_dependency = get_db(session_factory)

    @router.post("/preview", status_code=201)
    def preview(payload: PreviewRequest, request: Request, session: Session = Depends(db_dependency)):
        require_role_or_legacy(session, request, org_id=payload.org_id, roles={"owner", "operator"})
        if os.getenv("AGENCY_ENV", "development").strip().lower() == "production":
            configured = os.getenv("AGENCY_DEPLOY_PROVIDER", "").strip().lower()
            if payload.provider.strip().lower() != configured:
                raise HTTPException(status_code=400, detail="production deployment provider override is not allowed")
        try:
            deploy = create_preview(
                session,
                org_id=payload.org_id,
                client_id=payload.client_id,
                site_version_id=payload.site_version_id,
                provider=get_deployment_provider(payload.provider),
            )
            return {
                "deploy_id": deploy.id,
                "site_version_id": deploy.site_version_id,
                "provider": deploy.provider,
                "status": deploy.status,
                "url": deploy.url,
                "state": "PREVIEW_READY",
            }
        except (DeployError, NotImplementedError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/publish", status_code=201)
    def publish(payload: PublishRequest, request: Request, session: Session = Depends(db_dependency)):
        require_role_or_legacy(session, request, org_id=payload.org_id, roles={"owner", "operator"})
        try:
            deploy = publish_site(
                session,
                org_id=payload.org_id,
                client_id=payload.client_id,
                site_version_id=payload.site_version_id,
            )
            return {
                "deploy_id": deploy.id,
                "site_version_id": deploy.site_version_id,
                "provider": deploy.provider,
                "status": deploy.status,
                "url": deploy.url,
                "state": "LIVE",
            }
        except (DeployError, NotImplementedError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/rollback", status_code=201)
    def rollback(payload: RollbackRequest, request: Request, session: Session = Depends(db_dependency)):
        require_role_or_legacy(session, request, org_id=payload.org_id, roles={"owner", "operator"})
        try:
            deploy = rollback_site(
                session,
                org_id=payload.org_id,
                client_id=payload.client_id,
                build_hash=payload.build_hash,
            )
            return {
                "deploy_id": deploy.id,
                "site_version_id": deploy.site_version_id,
                "provider": deploy.provider,
                "status": deploy.status,
                "url": deploy.url,
                "state": "LIVE",
                "build_hash": payload.build_hash,
            }
        except (DeployError, NotImplementedError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/domain", status_code=200)
    def domain(payload: DomainRequest, request: Request, session: Session = Depends(db_dependency)):
        require_role_or_legacy(session, request, org_id=payload.org_id, roles={"owner", "operator"})
        try:
            result = attach_domain(
                session,
                org_id=payload.org_id,
                client_id=payload.client_id,
                fqdn=payload.fqdn,
            )
            return {"provider": result.provider, "fqdn": result.fqdn, "status": result.status}
        except (DeployError, NotImplementedError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/logs", status_code=200)
    def logs(payload: DeploymentLogsRequest, request: Request, session: Session = Depends(db_dependency)):
        require_role_or_legacy(session, request, org_id=payload.org_id, roles={"owner", "operator"})
        try:
            return {"deploy_id": payload.deploy_id, "logs": deployment_logs(
                session,
                org_id=payload.org_id,
                client_id=payload.client_id,
                deploy_id=payload.deploy_id,
            )}
        except (DeployError, NotImplementedError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
