"""Publish-approval endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, sessionmaker

from agency.api.auth_dependencies import require_role_or_legacy
from agency.api.dependencies import get_db
from agency.application.publish_approval import PublishApprovalError, approve_publish


class PublishApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    build_artifact_id: UUID
    approved_by: str = Field(min_length=1, max_length=255)
    feedback: str | None = Field(default=None, max_length=5000)


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/publish", tags=["publish"])
    db_dependency = get_db(session_factory)

    @router.post("/approve", status_code=200)
    def approve(
        payload: PublishApprovalRequest,
        request: Request,
        session: Session = Depends(db_dependency),
    ):
        membership = require_role_or_legacy(
            session, request, org_id=payload.org_id, roles={"owner", "reviewer"}
        )
        if membership is not None:
            payload = payload.model_copy(update={"approved_by": str(membership.user_id)})
        try:
            artifact = approve_publish(
                session,
                org_id=payload.org_id,
                client_id=payload.client_id,
                build_artifact_id=payload.build_artifact_id,
                approved_by=payload.approved_by,
                feedback=payload.feedback,
            )
            return {
                "build_artifact_id": artifact.id,
                "build_hash": artifact.build_hash,
                "state": "PREVIEW_APPROVED",
            }
        except PublishApprovalError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
