"""Client review-loop endpoints: change requests, revisions and decisions."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, sessionmaker

from agency.api.auth_dependencies import require_role_or_legacy
from agency.api.dependencies import get_db
from agency.services.change_request_service import (
    ChangeRequestError,
    create_change_request as svc_create_change_request,
    resolve_change_request as svc_resolve_change_request,
    start_revision as svc_start_revision,
    start_llm_revision as svc_start_llm_revision,
)


class ChangeRequestCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    site_version_id: UUID
    requested_by: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=5000)


class RevisionStartRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    org_id: UUID
    client_id: UUID
    change_request_id: UUID
    approved_by: str = Field(min_length=1, max_length=255)


class LLMRevisionStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    change_request_id: UUID
    instruction: str | None = Field(default=None, max_length=5000)
    provider: str | None = Field(default=None, max_length=64)
    approved_by: str = Field(min_length=1, max_length=255)


class ChangeRequestResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    org_id: UUID
    client_id: UUID
    change_request_id: UUID
    site_version_id: UUID
    build_hash: str
    approved_by: str = Field(min_length=1, max_length=255)
    decision: Literal["resolved", "rejected"] = "resolved"


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/review", tags=["review"])
    db_dependency = get_db(session_factory)

    @router.post("/request", status_code=201)
    def request_change(
        payload: ChangeRequestCreateRequest,
        request: Request,
        session: Session = Depends(db_dependency),
    ):
        require_role_or_legacy(session, request, org_id=payload.org_id, roles={"owner", "operator"})
        try:
            cr = svc_create_change_request(
                session,
                org_id=payload.org_id,
                client_id=payload.client_id,
                site_version_id=payload.site_version_id,
                requested_by=payload.requested_by,
                body=payload.body,
            )
            return {"change_request_id": cr.id, "status": cr.status}
        except ChangeRequestError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/revision", status_code=201)
    def start_revision(
        payload: RevisionStartRequest,
        request: Request,
        session: Session = Depends(db_dependency),
    ):
        require_role_or_legacy(session, request, org_id=payload.org_id, roles={"owner", "operator"})
        data = payload.model_dump(exclude={"org_id", "client_id", "change_request_id", "approved_by"})
        try:
            artifact = svc_start_revision(
                session,
                org_id=payload.org_id,
                client_id=payload.client_id,
                change_request_id=payload.change_request_id,
                content=data,
                approved_by=payload.approved_by,
            )
            return {"content_artifact_id": artifact.id, "revision": artifact.revision}
        except ChangeRequestError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/revision/llm", status_code=201)
    def start_llm_revision(
        payload: LLMRevisionStartRequest,
        request: Request,
        session: Session = Depends(db_dependency),
    ):
        require_role_or_legacy(session, request, org_id=payload.org_id, roles={"owner", "operator"})
        try:
            artifact = svc_start_llm_revision(
                session,
                org_id=payload.org_id,
                client_id=payload.client_id,
                change_request_id=payload.change_request_id,
                instruction=payload.instruction,
                provider_name=payload.provider,
                approved_by=payload.approved_by,
            )
            return {"content_artifact_id": artifact.id, "revision": artifact.revision}
        except ChangeRequestError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/resolve", status_code=200)
    def resolve(
        payload: ChangeRequestResolveRequest,
        request: Request,
        session: Session = Depends(db_dependency),
    ):
        require_role_or_legacy(session, request, org_id=payload.org_id, roles={"owner", "reviewer"})
        try:
            cr = svc_resolve_change_request(
                session,
                org_id=payload.org_id,
                client_id=payload.client_id,
                change_request_id=payload.change_request_id,
                site_version_id=payload.site_version_id,
                build_hash=payload.build_hash,
                approved_by=payload.approved_by,
                decision=payload.decision,
            )
            return {"change_request_id": cr.id, "status": cr.status}
        except ChangeRequestError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router