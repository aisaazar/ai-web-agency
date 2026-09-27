"""Tenant-scoped pipeline run persistence."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.workflow_models import PipelineRun


class PipelineRepository:
    def __init__(self, session: Session, org_id):
        self.session = session
        self.org_id = org_id

    def latest_for_client(self, client_id) -> PipelineRun | None:
        return self.session.scalar(
            select(PipelineRun)
            .where(PipelineRun.org_id == self.org_id, PipelineRun.client_id == client_id)
            .order_by(PipelineRun.created_at.desc())
        )

    def add(self, run: PipelineRun) -> PipelineRun:
        if run.org_id != self.org_id:
            raise ValueError("pipeline org_id does not match repository org_id")
        self.session.add(run)
        self.session.flush()
        return run
