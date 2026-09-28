"""Read-only dashboard projection service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.llm_budget_models import ClientLLMBudget
from agency.db.models import Approval, Artifact, Client, ClientFact, Deploy, LLMInvocation, LeadSubmission, Org, Site, SiteVersion
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

def get_client_detail(session: Session, *, org_id: UUID, client_id: UUID) -> dict:
    client = session.scalar(
        select(Client).where(Client.org_id == org_id, Client.id == client_id)
    )
    if client is None:
        raise ValueError("client not found")

    pipeline = session.scalars(
        select(PipelineRun)
        .where(PipelineRun.org_id == org_id, PipelineRun.client_id == client_id)
        .order_by(PipelineRun.created_at.desc())
    ).first()
    state = pipeline.state if pipeline is not None else "INTAKE"

    facts = list(
        session.scalars(
            select(ClientFact)
            .where(ClientFact.org_id == org_id, ClientFact.client_id == client_id)
            .order_by(ClientFact.key.asc(), ClientFact.created_at.asc())
        )
    )

    all_artifacts = list(
        session.scalars(
            select(Artifact)
            .where(Artifact.org_id == org_id)
            .order_by(Artifact.created_at.desc())
        )
    )
    by_id = {str(artifact.id): artifact for artifact in all_artifacts}

    def belongs(artifact: Artifact) -> bool:
        payload_client = artifact.payload_json.get("client_id")
        if payload_client == str(client_id):
            return True
        input_id = artifact.input_artifact_id
        if input_id and str(input_id) in by_id:
            source = by_id[str(input_id)]
            return source.payload_json.get("client_id") == str(client_id)
        return False

    artifacts = [artifact for artifact in all_artifacts if belongs(artifact)]
    artifact_ids = {artifact.id for artifact in artifacts}

    approvals = list(
        session.scalars(
            select(Approval)
            .where(
                Approval.org_id == org_id,
                Approval.artifact_id.in_(artifact_ids),
            )
            .order_by(Approval.created_at.asc())
        )
    ) if artifact_ids else []

    site = session.scalar(
        select(Site).where(Site.org_id == org_id, Site.client_id == client_id)
    )
    site_versions = list(
        session.scalars(
            select(SiteVersion)
            .where(SiteVersion.org_id == org_id, SiteVersion.site_id == site.id)
            .order_by(SiteVersion.created_at.desc())
        )
    ) if site else []

    deployments = list(
        session.scalars(
            select(Deploy)
            .where(
                Deploy.org_id == org_id,
                Deploy.site_version_id.in_([version.id for version in site_versions]),
            )
            .order_by(Deploy.created_at.desc())
        )
    ) if site_versions else []

    return {
        "org_id": org_id,
        "client": {
            "id": client.id,
            "name": client.name,
            "category": client.category,
            "state": state,
            "updated_at": client.updated_at,
            "live_url": site.live_url if site else None,
            "current_build_hash": site.current_build_hash if site else None,
        },
        "facts": [
            {
                "id": fact.id,
                "key": fact.key,
                "value": fact.value,
                "value_type": fact.value_type,
                "source_kind": fact.source_kind,
                "source_ref": fact.source_ref,
                "confidence": fact.confidence,
                "status": fact.status,
                "approved_by": fact.approved_by,
                "created_at": fact.created_at,
            }
            for fact in facts
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
        "approvals": [
            {
                "id": approval.id,
                "artifact_id": approval.artifact_id,
                "gate": approval.gate,
                "decision": approval.decision,
                "feedback": approval.feedback,
                "approved_by": approval.approved_by,
                "created_at": approval.created_at,
            }
            for approval in approvals
        ],
        "site_versions": [
            {
                "id": version.id,
                "build_hash": version.build_hash,
                "content_artifact_id": version.content_artifact_id,
                "template_version": version.template_version,
                "design_preset_id": version.design_preset_id,
                "created_at": version.created_at,
            }
            for version in site_versions
        ],
        "deployments": [
            {
                "id": deployment.id,
                "client": client.name,
                "provider": deployment.provider,
                "environment": deployment.environment,
                "status": deployment.status,
                "url": deployment.url,
                "created_at": deployment.created_at,
            }
            for deployment in deployments
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
