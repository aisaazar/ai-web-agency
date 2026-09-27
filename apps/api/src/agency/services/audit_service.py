"""Small, transaction-aware audit log writer."""

from uuid import UUID

from sqlalchemy.orm import Session

from agency.db.auth_models import AuditLog


def record_audit(
    session: Session,
    *,
    org_id,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    ip: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        org_id=org_id if isinstance(org_id, UUID) else UUID(str(org_id)),
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json=before,
        after_json=after,
        ip=ip,
    )
    session.add(entry)
    session.flush()
    return entry
