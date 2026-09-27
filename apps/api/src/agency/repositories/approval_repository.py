"""Tenant-scoped approvals."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Approval


class ApprovalRepository:
    def __init__(self, session: Session, org_id):
        self.session = session
        self.org_id = org_id

    def for_artifact(self, artifact_id) -> list[Approval]:
        return list(self.session.scalars(
            select(Approval).where(
                Approval.org_id == self.org_id,
                Approval.artifact_id == artifact_id,
            ).order_by(Approval.created_at.desc())
        ))

    def add(self, approval: Approval) -> Approval:
        if approval.org_id != self.org_id:
            raise ValueError("approval org_id does not match repository org_id")
        self.session.add(approval)
        self.session.flush()
        return approval
