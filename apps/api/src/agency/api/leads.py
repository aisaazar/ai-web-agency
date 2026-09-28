"""Public lead-capture and lifecycle endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session, sessionmaker

from agency.api.auth_dependencies import require_role_or_legacy, role_dependency
from agency.api.dependencies import get_db
from agency.api.schemas import (
    LeadEventOut,
    LeadListItemOut,
    LeadStatusUpdateIn,
    LeadSubmissionIn,
    LeadSubmissionOut,
)
from agency.services.lead_service import (
    create_lead,
    export_leads_csv,
    list_lead_events,
    list_leads,
    update_lead_status,
)


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/leads", tags=["leads"])
    db_dependency = get_db(session_factory)
    lead_editor = role_dependency(session_factory, {"owner", "operator"})

    @router.post("", response_model=LeadSubmissionOut, status_code=201)
    def submit_lead(payload: LeadSubmissionIn, request: Request, session: Session = Depends(db_dependency)):
        remote_ip = request.client.host if request.client else None
        return create_lead(session, payload, remote_ip=remote_ip)

    @router.get("", response_model=list[LeadListItemOut])
    def list_all(org_id: UUID, request: Request, session: Session = Depends(db_dependency)):
        require_role_or_legacy(session, request, org_id=org_id, roles={"owner", "operator", "reviewer"})
        return list_leads(session, org_id=org_id)

    @router.get("/export.csv")
    def export_csv(org_id: UUID, request: Request, session: Session = Depends(db_dependency)):
        require_role_or_legacy(session, request, org_id=org_id, roles={"owner", "operator", "reviewer"})
        return Response(
            content=export_leads_csv(session, org_id=org_id),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": "attachment; filename=leads.csv"},
        )

    @router.patch("/{lead_id}/status", response_model=LeadSubmissionOut)
    def change_status(
        lead_id: UUID,
        org_id: UUID,
        payload: LeadStatusUpdateIn,
        session: Session = Depends(db_dependency),
        membership=Depends(lead_editor),
    ):
        update = LeadStatusUpdateIn(
            status=payload.status,
            actor=str(membership.user_id),
            note=payload.note,
        )
        return update_lead_status(
            session,
            org_id=org_id,
            lead_id=lead_id,
            update=update,
        )

    @router.get("/{lead_id}/events", response_model=list[LeadEventOut])
    def events(
        lead_id: UUID,
        org_id: UUID,
        request: Request,
        session: Session = Depends(db_dependency),
    ):
        require_role_or_legacy(session, request, org_id=org_id, roles={"owner", "operator", "reviewer"})
        return list_lead_events(
            session,
            org_id=org_id,
            lead_id=lead_id,
        )

    return router
