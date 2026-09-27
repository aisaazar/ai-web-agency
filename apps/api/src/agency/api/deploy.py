"""Deployment endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, sessionmaker

from agency.api.dependencies import get_db
from agency.services.deploy_service import DeployError, publish_site


class PublishRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    site_version_id: UUID


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/deploys", tags=["deployments"])
    db_dependency = get_db(session_factory)

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
        except DeployError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
