"""Public lead-capture and lifecycle endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, sessionmaker

from agency.api.dependencies import get_db
from agency.api.schemas import (
    LeadEventOut,
    LeadStatusUpdateIn,
    LeadSubmissionIn,
    LeadSubmissionOut,
)
from agency.services.lead_service import (
    create_lead,
    list_lead_events,
    update_lead_status,
)


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/leads", tags=["leads"])
    db_dependency = get_db(session_factory)

    @router.post("", response_model=LeadSubmissionOut, status_code=201)
    def submit_lead(payload: LeadSubmissionIn, session: Session = Depends(db_dependency)):
        return create_lead(session, payload)

    @router.patch("/{lead_id}/status", response_model=LeadSubmissionOut)
    def change_status(
        lead_id: UUID,
        org_id: UUID,
        payload: LeadStatusUpdateIn,
        session: Session = Depends(db_dependency),
    ):
        return update_lead_status(
            session,
            org_id=org_id,
            lead_id=lead_id,
            update=payload,
        )

    @router.get("/{lead_id}/events", response_model=list[LeadEventOut])
    def events(
        lead_id: UUID,
        org_id: UUID,
        session: Session = Depends(db_dependency),
    ):
        return list_lead_events(
            session,
            org_id=org_id,
            lead_id=lead_id,
        )

    return router
