"""Deterministic design endpoint."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, sessionmaker

from agency.api.dependencies import get_db
from agency.services.design_service import DesignError, design_site


class DesignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    content_artifact_id: UUID
    preset_id: str = Field(default="health", min_length=1, max_length=100)
    template_version: str = Field(default="1.0.0", min_length=1, max_length=64)


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/design", tags=["design"])
    db_dependency = get_db(session_factory)

    @router.post("", status_code=201)
    def design(payload: DesignRequest, session: Session = Depends(db_dependency)):
        try:
            artifact = design_site(
                session,
                org_id=payload.org_id,
                client_id=payload.client_id,
                content_artifact_id=payload.content_artifact_id,
                preset_id=payload.preset_id,
                template_version=payload.template_version,
            )
            return {"artifact_id": artifact.id, "state": "DESIGN_APPROVED"}
        except DesignError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
