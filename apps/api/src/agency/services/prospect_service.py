"""Deterministic prospect intake and prioritization for client acquisition."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from agency.api.prospect_schemas import (
    ProspectCreateIn,
    ProspectOut,
    ProspectStatusUpdateIn,
)
from agency.db.models import Prospect
from agency.repositories.prospect_repository import ProspectRepository
from agency.services.audit_service import record_audit

_TARGET_CATEGORIES = {
    "dental", "dentist", "praxis", "health", "medical", "beauty",
    "salon", "physio", "physiotherapy", "law", "lawyer", "accounting",
    "restaurant", "hospitality", "real estate", "professional services",
    "local business",
}


def _scores(payload: ProspectCreateIn) -> tuple[int, int]:
    category = payload.category.strip().lower()
    fit = 40 if category in _TARGET_CATEGORIES else 24
    if payload.city:
        fit += 10
    if payload.contactability in {"email", "phone", "email+phone"}:
        fit += 10
    fit = min(fit, 60)

    opportunity = 15
    opportunity += {
        "missing": 45, "poor": 32, "unknown": 18, "good": 0,
    }[payload.website_status]
    opportunity += {
        "email+phone": 20, "email": 14, "phone": 10, "unknown": 0,
    }.get(payload.contactability, 0)
    if payload.source_url:
        opportunity += 5
    return fit, min(opportunity, 100)


def _out(prospect: Prospect) -> ProspectOut:
    return ProspectOut.model_validate(prospect, from_attributes=True)


def create_prospect(
    session: Session, payload: ProspectCreateIn, *, actor: str
) -> ProspectOut:
    fit_score, opportunity_score = _scores(payload)
    prospect = Prospect(
        org_id=payload.org_id,
        name=payload.name.strip(),
        category=payload.category.strip(),
        city=payload.city.strip() if payload.city else None,
        country=payload.country.strip().upper(),
        website_url=payload.website_url.strip() if payload.website_url else None,
        source_url=payload.source_url.strip() if payload.source_url else None,
        source_kind=payload.source_kind.strip().lower(),
        contactability=payload.contactability.strip().lower(),
        website_status=payload.website_status,
        fit_score=fit_score,
        opportunity_score=opportunity_score,
        status="new",
        notes=payload.notes.strip() if payload.notes else None,
    )
    ProspectRepository(session, payload.org_id).add(prospect)
    record_audit(
        session,
        org_id=payload.org_id,
        actor=actor,
        action="prospect.created",
        entity_type="prospect",
        entity_id=str(prospect.id),
        after={
            "name": prospect.name,
            "website_status": prospect.website_status,
            "opportunity_score": prospect.opportunity_score,
        },
    )
    return _out(prospect)



def list_prospects(session: Session, *, org_id) -> list[ProspectOut]:
    return [_out(item) for item in ProspectRepository(session, org_id).list()]


def update_prospect_status(
    session: Session,
    *,
    org_id,
    prospect_id,
    update: ProspectStatusUpdateIn,
    actor: str,
) -> ProspectOut:
    repo = ProspectRepository(session, org_id)
    prospect = repo.get(prospect_id)
    if prospect is None:
        raise HTTPException(status_code=404, detail="Prospect not found")
    previous = prospect.status
    if previous == update.status:
        raise HTTPException(
            status_code=400, detail="Prospect is already in that status"
        )
    prospect.status = update.status
    if update.note:
        prospect.notes = update.note
    record_audit(
        session,
        org_id=org_id,
        actor=actor,
        action="prospect.status_updated",
        entity_type="prospect",
        entity_id=str(prospect.id),
        before={"status": previous},
        after={"status": update.status, "note": update.note},
    )
    return _out(prospect)
