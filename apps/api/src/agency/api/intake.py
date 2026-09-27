"""Admin intake endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, sessionmaker

from agency.api.auth_dependencies import require_role_or_legacy
from agency.api.dependencies import get_db
from agency.api.intake_schemas import IntakeRequest, IntakeResponse
from agency.application.intake import IntakeError, submit_intake


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/intake", tags=["intake"])
    db_dependency = get_db(session_factory)

    @router.post("", response_model=IntakeResponse, status_code=201)
    def intake(payload: IntakeRequest, request: Request, session: Session = Depends(db_dependency)):
        require_role_or_legacy(session, request, org_id=payload.org_id, roles={"owner", "operator"})
        try:
            return submit_intake(session, payload)
        except IntakeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
