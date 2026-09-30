"""Content generation and approval endpoints."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, sessionmaker

from agency.api.auth_dependencies import require_role_or_legacy
from agency.api.dependencies import get_db
from agency.application.content_approval import ContentApprovalError, approve_content
from agency.services.content_ai_service import AIContentGenerationError, generate_content_with_llm
from agency.services.content_service import ContentGenerationError, generate_content


class ContentGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    org_id: UUID
    client_id: UUID
    mode: Literal["payload", "llm"] = "payload"
    instruction: str | None = Field(default=None, max_length=5000)
    provider: str | None = Field(default=None, max_length=64)


class ContentApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    artifact_id: UUID
    approved_by: str = Field(min_length=1, max_length=255)
    feedback: str | None = Field(default=None, max_length=5000)


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/content", tags=["content"])
    db_dependency = get_db(session_factory)

    @router.post("", status_code=201)
    def generate(payload: ContentGenerationRequest, request: Request, session: Session = Depends(db_dependency)):
        require_role_or_legacy(session, request, org_id=payload.org_id, roles={"owner", "operator"})
        try:
            if payload.mode == "llm":
                artifact = generate_content_with_llm(
                    session,
                    org_id=payload.org_id,
                    client_id=payload.client_id,
                    instruction=payload.instruction,
                    provider_name=payload.provider,
                )
            else:
                data = payload.model_dump(
                    exclude={"org_id", "client_id", "mode", "instruction", "provider"}
                )
                artifact = generate_content(
                    session,
                    org_id=payload.org_id,
                    client_id=payload.client_id,
                    payload=data,
                )
            return {
                "id": artifact.id,
                "artifact_type": artifact.artifact_type,
                "state": "CONTENT_COMPLETE",
            }
        except (ContentGenerationError, AIContentGenerationError) as exc:
            # The service already recorded the recoverable FAILED state, the audit entry,
            # and the cost of the LLM calls that really happened. get_db rolls back on a
            # raised HTTPException, so persist that diagnostic transaction first: without
            # it failures are invisible and paid LLM spend stops counting towards budget.
            session.commit()
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/approve", status_code=200)
    def approve(payload: ContentApprovalRequest, request: Request, session: Session = Depends(db_dependency)):
        membership = require_role_or_legacy(
            session, request, org_id=payload.org_id, roles={"owner", "reviewer"}
        )
        if membership is not None:
            payload = payload.model_copy(update={"approved_by": str(membership.user_id)})
        try:
            artifact = approve_content(
                session,
                org_id=payload.org_id,
                client_id=payload.client_id,
                artifact_id=payload.artifact_id,
                approved_by=payload.approved_by,
                feedback=payload.feedback,
            )
            return {"artifact_id": artifact.id, "state": "CONTENT_APPROVED"}
        except ContentApprovalError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
