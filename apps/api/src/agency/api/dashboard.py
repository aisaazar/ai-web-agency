"""Dashboard read endpoints backed by persisted agency data."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from agency.api.auth_dependencies import require_role_or_legacy
from agency.api.dashboard_schemas import DashboardOverviewOut
from agency.api.dependencies import get_db
from agency.db.models import Artifact, Client, Deploy, LeadSubmission, Org, Site, SiteVersion
from agency.db.workflow_models import PipelineRun
from agency.services.dashboard_service import get_overview


def build_router(session_factory: sessionmaker[Session]) -> APIRouter:
    router = APIRouter(prefix="/v1/dashboard", tags=["dashboard"])
    db_dependency = get_db(session_factory)

    @router.get("/overview", response_model=DashboardOverviewOut)
    def overview(org_id: UUID, request: Request, session: Session = Depends(db_dependency)):
        require_role_or_legacy(session, request, org_id=org_id, roles={"owner", "operator", "reviewer"})
        return get_overview(session, org_id=org_id)

    @router.get("")
    def dashboard(org_id: UUID | None = None, request: Request = None, session: Session = Depends(db_dependency)):
        if org_id is not None:
            require_role_or_legacy(session, request, org_id=org_id, roles={"owner", "operator", "reviewer"})
        if org_id is None:
            org_ids = list(session.scalars(select(Org.id).order_by(Org.created_at)))
            if len(org_ids) > 1:
                raise HTTPException(status_code=400, detail="org_id is required when multiple organizations exist")
            if not org_ids:
                return {"clients": [], "artifacts": [], "deployments": [], "leads": []}
            org_id = org_ids[0]

        require_role_or_legacy(session, request, org_id=org_id, roles={"owner", "operator", "reviewer"})

        clients = list(session.scalars(
            select(Client).where(Client.org_id == org_id).order_by(Client.name)
        ))
        artifacts = list(session.scalars(
            select(Artifact).where(Artifact.org_id == org_id).order_by(Artifact.created_at.desc())
        ))
        deployments = list(session.scalars(
            select(Deploy).where(Deploy.org_id == org_id).order_by(Deploy.created_at.desc())
        ))
        site_client_ids = {
            str(version.id): str(site.client_id)
            for version, site in session.execute(
                select(SiteVersion, Site)
                .where(
                    SiteVersion.org_id == org_id,
                    SiteVersion.site_id == Site.id,
                    Site.org_id == org_id,
                )
            ).all()
        }
        leads = list(session.scalars(
            select(LeadSubmission).where(LeadSubmission.org_id == org_id).order_by(LeadSubmission.created_at.desc())
        ))
        pipeline = {}
        for run in session.scalars(
            select(PipelineRun).where(PipelineRun.org_id == org_id).order_by(PipelineRun.created_at.desc())
        ):
            pipeline.setdefault(str(run.client_id), run.state)

        return {
            "clients": [
                {"id": str(c.id), "name": c.name, "category": c.category,
                 "state": pipeline.get(str(c.id), "INTAKE"),
                 "updatedAt": c.updated_at.isoformat()}
                for c in clients
            ],
            "artifacts": [
                {"id": str(a.id), "type": a.artifact_type, "revision": a.revision,
                 "status": "active" if a.is_active else "pending", "buildHash": a.build_hash}
                for a in artifacts
            ],
            "deployments": [
                {"id": str(d.id), "client": next(
                    (c.name for c in clients if str(c.id) == site_client_ids.get(str(d.site_version_id))),
                    site_client_ids.get(str(d.site_version_id), "unknown"),
                ),
                 "provider": d.provider, "status": d.status, "url": d.url}
                for d in deployments
            ],
            "leads": [
                {"id": str(l.id), "client": next((c.name for c in clients if c.id == l.client_id), str(l.client_id)),
                 "name": l.name, "status": l.status, "createdAt": l.created_at.isoformat()}
                for l in leads
            ],
        }

    return router
