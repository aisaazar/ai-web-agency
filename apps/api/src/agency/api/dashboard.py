"""Dashboard read endpoints backed by persisted agency data."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, sessionmaker

from agency.api.auth_dependencies import require_role_or_legacy
from agency.api.dashboard_schemas import DashboardClientDetailOut, DashboardLLMCostOut, DashboardOverviewOut
from agency.api.dependencies import get_db
from agency.services.dashboard_service import get_client_detail, get_llm_cost_report, get_overview


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])
    db_dependency = get_db(session_factory)

    @router.get("/overview", response_model=DashboardOverviewOut)
    def overview(org_id: UUID, request: Request, session: Session = Depends(db_dependency)):
        require_role_or_legacy(session, request, org_id=org_id, roles={"owner", "operator", "reviewer"})
        return get_overview(session, org_id=org_id)

    @router.get("/clients/{client_id}", response_model=DashboardClientDetailOut)
    def client_detail(
        client_id: UUID,
        org_id: UUID,
        request: Request,
        session: Session = Depends(db_dependency),
    ):
        require_role_or_legacy(
            session, request, org_id=org_id, roles={"owner", "operator", "reviewer"}
        )
        try:
            return get_client_detail(session, org_id=org_id, client_id=client_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get("/llm-cost", response_model=DashboardLLMCostOut)
    def llm_cost(org_id: UUID, request: Request, session: Session = Depends(db_dependency)):
        require_role_or_legacy(session, request, org_id=org_id, roles={"owner", "operator", "reviewer"})
        return get_llm_cost_report(session, org_id=org_id)

    return router

