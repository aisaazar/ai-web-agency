"""Deployment endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, sessionmaker

from agency.api.dependencies import get_db
from agency.providers.deployment_registry import get_deployment_provider
from agency.services.deploy_service import DeployError, create_preview, publish_site, rollback_site


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


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/deploys", tags=["deployments"])
    db_dependency = get_db(session_factory)

    @router.post("/preview", status_code=201)
    def preview(payload: PreviewRequest, session: Session = Depends(db_dependency)):
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
    def publish(payload: PublishRequest, session: Session = Depends(db_dependency)):
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
    def rollback(payload: RollbackRequest, session: Session = Depends(db_dependency)):
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

    return router
