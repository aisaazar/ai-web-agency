"""Authenticated acquisition prospect endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, sessionmaker

from agency.api.auth_dependencies import role_dependency
from agency.api.dependencies import get_db
from agency.api.prospect_schemas import (
    ProspectCreateIn,
    ProspectOut,
    ProspectStatusUpdateIn,
)
from agency.services.prospect_service import (
    create_prospect,
    list_prospects,
    update_prospect_status,
)


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/prospects", tags=["prospects"])
    db = get_db(session_factory)
    editor = role_dependency(session_factory, {"owner", "operator"})
    viewer = role_dependency(
        session_factory, {"owner", "operator", "reviewer"}
    )

    @router.get("", response_model=list[ProspectOut])
    def list_all(
        org_id: UUID,
        membership=Depends(viewer),
        session: Session = Depends(db),
    ):
        return list_prospects(session, org_id=org_id)


    @router.post("", response_model=ProspectOut, status_code=201)
    def create(
        org_id: UUID,
        payload: ProspectCreateIn,
        membership=Depends(editor),
        session: Session = Depends(db),
    ):
        if payload.org_id != org_id:
            raise HTTPException(status_code=400, detail="payload org_id does not match authorized org")
        return create_prospect(
            session, payload, actor=str(membership.user_id)
        )

    @router.patch(
        "/{prospect_id}/status", response_model=ProspectOut
    )
    def update_status(
        prospect_id: UUID,
        org_id: UUID,
        payload: ProspectStatusUpdateIn,
        membership=Depends(editor),
        session: Session = Depends(db),
    ):
        return update_prospect_status(
            session,
            org_id=org_id,
            prospect_id=prospect_id,
            update=payload,
            actor=str(membership.user_id),
        )

    return router
