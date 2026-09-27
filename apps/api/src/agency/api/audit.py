"""Tenant audit log read endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from agency.api.auth_dependencies import role_dependency
from agency.api.dependencies import get_db
from agency.db.auth_models import AuditLog


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/audit", tags=["audit"])
    db = get_db(session_factory)
    owner = role_dependency(session_factory, {"owner"})

    @router.get("")
    def list_audit(
        org_id: UUID,
        limit: int = 50,
        session: Session = Depends(db),
        _membership=Depends(owner),
    ):
        limit = max(1, min(limit, 200))
        rows = session.scalars(
            select(AuditLog)
            .where(AuditLog.org_id == org_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        return [
            {
                "id": str(row.id),
                "actor": row.actor,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "before": row.before_json,
                "after": row.after_json,
                "ip": row.ip,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    return router
