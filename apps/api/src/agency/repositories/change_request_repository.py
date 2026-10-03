"""Tenant-scoped change-request persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import ChangeRequest


class ChangeRequestRepository:
    def __init__(self, session: Session, org_id):
        self.session = session
        self.org_id = org_id

    def get(self, change_request_id) -> ChangeRequest | None:
        return self.session.scalar(
            select(ChangeRequest).where(
                ChangeRequest.id == change_request_id,
                ChangeRequest.org_id == self.org_id,
            )
        )

    def for_client(self, client_id) -> list[ChangeRequest]:
        # `client_id` is a `Uuid` column: bind a real UUID so SQLAlchemy's Uuid type can encode it.
        return list(self.session.scalars(
            select(ChangeRequest).where(
                ChangeRequest.org_id == self.org_id,
                ChangeRequest.client_id == UUID(str(client_id)),
            ).order_by(ChangeRequest.created_at.desc())
        ))

    def add(self, change_request: ChangeRequest) -> ChangeRequest:
        if change_request.org_id != self.org_id:
            raise ValueError("change request org_id does not match repository org_id")
        self.session.add(change_request)
        self.session.flush()
        return change_request