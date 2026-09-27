"""Research execution and approval endpoints."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from agency.api.dependencies import get_db
from agency.db.models import Approval, Artifact
from agency.repositories import ApprovalRepository
from agency.repositories.pipeline_repository import PipelineRepository
from agency.services.pipeline_service import transition
from agency.services.research_service import run_research


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    provider: str = Field(default="mock", min_length=1, max_length=64)


class ResearchApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    artifact_id: UUID
    approved_by: str = Field(min_length=1, max_length=255)
    feedback: str | None = Field(default=None, max_length=5000)


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/research", tags=["research"])
    db_dependency = get_db(session_factory)

    @router.post("", status_code=201)
    def research(payload: ResearchRequest, session: Session = Depends(db_dependency)):
        try:
            artifact = run_research(
                session,
                org_id=payload.org_id,
                client_id=payload.client_id,
                provider_name=payload.provider,
            )
            return {"artifact_id": artifact.id, "state": "RESEARCH_COMPLETE"}
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/approve", status_code=200)
    def approve(payload: ResearchApprovalRequest, session: Session = Depends(db_dependency)):
        pipeline = PipelineRepository(session, payload.org_id).latest_for_client(payload.client_id)
        artifact = session.scalar(select(Artifact).where(
            Artifact.id == payload.artifact_id,
            Artifact.org_id == payload.org_id,
            Artifact.artifact_type == "research_report",
        ))
        if pipeline is None or pipeline.state != "RESEARCH_COMPLETE" or artifact is None:
            raise HTTPException(status_code=400, detail="research is not ready for approval")
        ApprovalRepository(session, payload.org_id).add(Approval(
            org_id=payload.org_id,
            artifact_id=artifact.id,
            gate="RESEARCH",
            decision="approved",
            feedback=payload.feedback,
            approved_by=payload.approved_by,
        ))
        pipeline.state = transition(pipeline.state, "RESEARCH_APPROVED").to_state
        return {"artifact_id": artifact.id, "state": pipeline.state}

    return router
