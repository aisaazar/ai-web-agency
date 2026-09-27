"""Artifact revision rules.

The caller owns the transaction. This service never commits, rolls back, or closes the session.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Artifact


def create_revision(
    session: Session,
    *,
    org_id,
    source: Artifact,
    payload_json: dict,
    schema_version: str,
) -> Artifact:
    if source.org_id != org_id:
        raise ValueError("artifact does not belong to org")
    if source.schema_version != schema_version:
        raise ValueError("schema version cannot change inside an artifact revision chain")

    active = session.scalar(
        select(Artifact).where(
            Artifact.id == source.id,
            Artifact.org_id == org_id,
            Artifact.is_active.is_(True),
        )
    )
    if active is None:
        raise ValueError("source artifact is not the active revision")

    active.is_active = False
    revision = Artifact(
        org_id=org_id,
        artifact_type=source.artifact_type,
        schema_version=schema_version,
        payload_json=payload_json,
        revision=source.revision + 1,
        input_artifact_id=source.id,
        is_active=True,
    )
    session.add(revision)
    session.flush()
    return revision
