"""Tenant-scoped artifact repository.

Artifact writes remain inside the caller's transaction boundary.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Artifact


class ArtifactRepository:
    def __init__(self, session: Session, org_id):
        self.session = session
        self.org_id = org_id

    def get(self, artifact_id):
        return self.session.scalar(
            select(Artifact).where(Artifact.id == artifact_id, Artifact.org_id == self.org_id)
        )

    def active_by_type(self, artifact_type: str) -> list[Artifact]:
        return list(
            self.session.scalars(
                select(Artifact)
                .where(
                    Artifact.org_id == self.org_id,
                    Artifact.artifact_type == artifact_type,
                    Artifact.is_active.is_(True),
                )
                .order_by(Artifact.created_at.desc())
            )
        )

    def add(self, artifact: Artifact) -> Artifact:
        if artifact.org_id != self.org_id:
            raise ValueError("artifact org_id does not match repository org_id")
        self.session.add(artifact)
        self.session.flush()
        return artifact
