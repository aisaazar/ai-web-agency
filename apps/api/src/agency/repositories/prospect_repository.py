"""Tenant-scoped repository for acquisition prospects."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Prospect


class ProspectRepository:
    def __init__(self, session: Session, org_id):
        self.session = session
        self.org_id = org_id

    def get(self, prospect_id):
        return self.session.scalar(
            select(Prospect).where(
                Prospect.id == prospect_id, Prospect.org_id == self.org_id
            )
        )

    def list(self) -> list[Prospect]:
        return list(
            self.session.scalars(
                select(Prospect)
                .where(Prospect.org_id == self.org_id)
                .order_by(
                    Prospect.opportunity_score.desc(), Prospect.created_at.desc()
                )
            )
        )

    def add(self, prospect: Prospect) -> Prospect:
        if prospect.org_id != self.org_id:
            raise ValueError("prospect org_id does not match repository org_id")
        self.session.add(prospect)
        self.session.flush()
        return prospect
