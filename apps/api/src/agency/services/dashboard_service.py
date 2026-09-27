"""Read-only dashboard projection service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.llm_budget_models import ClientLLMBudget
from agency.db.models import Artifact, Client, Deploy, LLMInvocation, LeadSubmission, Org, Site, SiteVersion
from agency.db.workflow_models import PipelineRun


def get_overview(session: Session, *, org_id: UUID) -> dict:
    clients = list(session.scalars(
        select(Client).where(Client.org_id == org_id).order_by(Client.name)
    ))
    artifacts = list(session.scalars(
        select(Artifact).where(Artifact.org_id == org_id).order_by(Artifact.created_at.desc())
    ))
    deployments = list(session.scalars(
        select(Deploy).where(Deploy.org_id == org_id).order_by(Deploy.created_at.desc())
    ))
    leads = list(session.scalars(
        select(LeadSubmission)
        .where(LeadSubmission.org_id == org_id)
        .order_by(LeadSubmission.created_at.desc())
    ))
    site_versions = list(session.execute(
        select(SiteVersion, Site).where(
            SiteVersion.org_id == org_id,
            SiteVersion.site_id == Site.id,
            Site.org_id == org_id,
        )
    ).all())
    site_clients = {str(version.id): str(site.client_id) for version, site in site_versions}
    sites_by_client = {str(site.client_id): site for _, site in site_versions}
    pipeline_states: dict[str, str] = {}
    for run in session.scalars(
        select(PipelineRun)
        .where(PipelineRun.org_id == org_id)
        .order_by(PipelineRun.created_at.desc())
    ):
        pipeline_states.setdefault(str(run.client_id), run.state)

    client_map = {str(client.id): client for client in clients}
    return {
        "org_id": org_id,
        "counts": {
            "clients": len(clients),
            "artifacts": len(artifacts),
            "deployments": len(deployments),
            "new_leads": sum(lead.status == "new" for lead in leads),
        },
        "clients": [
            {
                "id": client.id,
                "name": client.name,
                "category": client.category,
                "state": pipeline_states.get(str(client.id), "INTAKE"),
                "updated_at": client.updated_at,
                "live_url": sites_by_client.get(str(client.id)).live_url
                if sites_by_client.get(str(client.id)) else None,
                "current_build_hash": sites_by_client.get(str(client.id)).current_build_hash
                if sites_by_client.get(str(client.id)) else None,
            }
            for client in clients
        ],
        "artifacts": [
            {
                "id": artifact.id,
                "type": artifact.artifact_type,
                "revision": artifact.revision,
                "status": "active" if artifact.is_active else "archived",
                "build_hash": artifact.build_hash,
                "updated_at": artifact.updated_at,
            }
            for artifact in artifacts
        ],
        "deployments": [
            {
                "id": deployment.id,
                "client": client_map.get(
                    site_clients.get(str(deployment.site_version_id))
                ).name
                if client_map.get(site_clients.get(str(deployment.site_version_id))) else "unknown",
                "provider": deployment.provider,
                "environment": deployment.environment,
                "status": deployment.status,
                "url": deployment.url,
                "created_at": deployment.created_at,
            }
            for deployment in deployments
        ],
        "leads": [
            {
                "id": lead.id,
                "client": client_map.get(str(lead.client_id)).name
                if client_map.get(str(lead.client_id)) else "unknown",
                "name": lead.name,
                "status": lead.status,
                "email": lead.email,
                "received_at": lead.created_at,
            }
            for lead in leads
        ],
    }

def get_llm_cost_report(session: Session, *, org_id: UUID) -> dict:
    org = session.get(Org, org_id)
    if org is None:
        raise ValueError("organization not found")

    spent_rows = session.execute(
        select(LLMInvocation.client_id, LLMInvocation.cost_micros)
        .where(
            LLMInvocation.org_id == org_id,
            LLMInvocation.status == "completed",
        )
    ).all()
    spent_by_client: dict[str, int] = {}
    for client_id, cost in spent_rows:
        spent_by_client[str(client_id)] = spent_by_client.get(str(client_id), 0) + int(cost or 0)

    budgets = {
        str(row.client_id): int(row.budget_micros)
        for row in session.scalars(
            select(ClientLLMBudget).where(ClientLLMBudget.org_id == org_id)
        )
    }
    clients = list(
        session.scalars(
            select(Client).where(Client.org_id == org_id).order_by(Client.name)
        )
    )
    client_rows = [
        {
            "client_id": client.id,
            "client_name": client.name,
            "budget_micros": budgets.get(str(client.id), int(org.llm_budget_micros)),
            "spent_micros": spent_by_client.get(str(client.id), 0),
        }
        for client in clients
    ]
    return {
        "org_id": org_id,
        "budget_micros": int(org.llm_budget_micros),
        "spent_micros": sum(spent_by_client.values()),
        "clients": client_rows,
    }
