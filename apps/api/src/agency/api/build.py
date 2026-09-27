"""Static site build and preview-gate endpoint."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, sessionmaker

from agency.api.auth_dependencies import require_role_or_legacy
from agency.api.dependencies import get_db
from agency.services.site_build_service import SiteBuildError, build_site


class SiteBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    content_artifact_id: UUID
    design_artifact_id: UUID


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/builds", tags=["builds"])
    db_dependency = get_db(session_factory)

    @router.post("/site", status_code=201)
    def build(payload: SiteBuildRequest, request: Request, session: Session = Depends(db_dependency)):
        require_role_or_legacy(session, request, org_id=payload.org_id, roles={"owner", "operator"})
        try:
            version = build_site(
                session,
                org_id=payload.org_id,
                client_id=payload.client_id,
                content_artifact_id=payload.content_artifact_id,
                design_artifact_id=payload.design_artifact_id,
            )
            return {
                "site_version_id": version.id,
                "build_hash": version.build_hash,
                "state": "PREVIEW_READY",
            }
        except SiteBuildError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
