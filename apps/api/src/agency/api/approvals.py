"""Approval endpoints for internal workflow operations."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, sessionmaker

from agency.api.approval_schemas import FactsApprovalRequest, FactsApprovalResponse
from agency.api.dependencies import get_db
from agency.application.facts_approval import ApprovalError, approve_facts


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/approvals", tags=["approvals"])
    db_dependency = get_db(session_factory)

    @router.post("/facts", response_model=FactsApprovalResponse, status_code=200)
    def approve_facts_route(
        payload: FactsApprovalRequest,
        session: Session = Depends(db_dependency),
    ):
        try:
            return approve_facts(session, payload)
        except ApprovalError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
