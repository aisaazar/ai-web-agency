"""Tenant-scoped lead persistence."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import LeadEvent, LeadSubmission


class LeadRepository:
    def __init__(self, session: Session, org_id):
        self.session = session
        self.org_id = org_id

    def list_for_site(self, site_id) -> list[LeadSubmission]:
        return list(
            self.session.scalars(
                select(LeadSubmission)
                .where(
                    LeadSubmission.org_id == self.org_id,
                    LeadSubmission.site_id == site_id,
                )
                .order_by(LeadSubmission.created_at.desc())
            )
        )

    def list_all(self) -> list[LeadSubmission]:
        return list(
            self.session.scalars(
                select(LeadSubmission)
                .where(LeadSubmission.org_id == self.org_id)
                .order_by(LeadSubmission.created_at.desc())
            )
        )

    def get(self, lead_id) -> LeadSubmission | None:
        return self.session.scalar(
            select(LeadSubmission).where(
                LeadSubmission.org_id == self.org_id,
                LeadSubmission.id == lead_id,
            )
        )

    def events(self, lead_id) -> list[LeadEvent]:
        return list(
            self.session.scalars(
                select(LeadEvent)
                .where(
                    LeadEvent.org_id == self.org_id,
                    LeadEvent.lead_submission_id == lead_id,
                )
                .order_by(LeadEvent.created_at.asc())
            )
        )

    def add(self, lead: LeadSubmission) -> LeadSubmission:
        if lead.org_id != self.org_id:
            raise ValueError("lead org_id does not match repository org_id")
        self.session.add(lead)
        self.session.flush()
        return lead

    def add_event(self, event: LeadEvent) -> LeadEvent:
        if event.org_id != self.org_id:
            raise ValueError("lead event org_id does not match repository org_id")
        self.session.add(event)
        self.session.flush()
        return event
