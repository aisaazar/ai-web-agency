"""Lead capture and lifecycle use cases."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from agency.api.schemas import (
    LeadEventOut,
    LeadStatusUpdateIn,
    LeadSubmissionIn,
    LeadSubmissionOut,
)
from agency.db.models import Client, LeadEvent, LeadSubmission, Site
from agency.repositories import LeadRepository


def create_lead(session: Session, payload: LeadSubmissionIn) -> LeadSubmissionOut:
    if not payload.consent:
        raise HTTPException(status_code=400, detail="Consent is required")

    site = session.get(Site, payload.site_id)
    if site is None:
        raise HTTPException(status_code=404, detail="Site not found")
    client = session.get(Client, site.client_id)
    if client is None or client.org_id != site.org_id:
        raise HTTPException(status_code=404, detail="Site not found")

    now = datetime.now(timezone.utc)
    spam_score = 0
    lead_status = "new"
    if payload.website.strip():
        spam_score = 100
        lead_status = "spam"
    elif payload.form_started_at is not None:
        started = payload.form_started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if (now - started).total_seconds() < 2:
            spam_score = 10

    lead = LeadSubmission(
        org_id=site.org_id,
        site_id=site.id,
        client_id=client.id,
        payload_json=payload.model_dump(mode="json"),
        name=payload.name.strip(),
        email=payload.email.strip().lower(),
        phone=payload.phone.strip() if payload.phone else None,
        message=payload.message.strip(),
        consent_at=now,
        spam_score=spam_score,
        status=lead_status,
        utm_json=payload.utm,
    )
    repo = LeadRepository(session, site.org_id)
    repo.add(lead)
    repo.add_event(LeadEvent(
        org_id=site.org_id,
        lead_submission_id=lead.id,
        from_status=None,
        to_status=lead.status,
        actor="system",
        note="lead captured",
    ))
    return LeadSubmissionOut(id=lead.id, status=lead.status, received_at=lead.created_at)


def update_lead_status(
    session: Session,
    *,
    org_id,
    lead_id,
    update: LeadStatusUpdateIn,
) -> LeadSubmissionOut:
    repo = LeadRepository(session, org_id)
    lead = repo.get(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.status == "spam":
        raise HTTPException(status_code=400, detail="Spam leads cannot enter the sales workflow")
    if lead.status == update.status:
        raise HTTPException(status_code=400, detail="Lead is already in that status")

    previous = lead.status
    lead.status = update.status
    repo.add_event(LeadEvent(
        org_id=org_id,
        lead_submission_id=lead.id,
        from_status=previous,
        to_status=update.status,
        actor=update.actor,
        note=update.note,
    ))
    return LeadSubmissionOut(
        id=lead.id,
        status=lead.status,
        received_at=lead.created_at,
    )


def list_lead_events(
    session: Session,
    *,
    org_id,
    lead_id,
) -> list[LeadEventOut]:
    repo = LeadRepository(session, org_id)
    if repo.get(lead_id) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return [
        LeadEventOut(
            id=event.id,
            from_status=event.from_status,
            to_status=event.to_status,
            actor=event.actor,
            note=event.note,
            created_at=event.created_at,
        )
        for event in repo.events(lead_id)
    ]
