"""Facts approval: freeze approved facts into a versioned artifact."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.api.approval_schemas import FactsApprovalRequest, FactsApprovalResponse
from agency.db.models import Approval, Artifact, Client, ClientFact
from agency.db.workflow_models import PipelineRun
from agency.repositories import ApprovalRepository, ArtifactRepository, PipelineRepository
from agency.services.pipeline_service import transition


class ApprovalError(ValueError):
    """Raised when an approval request cannot be applied."""


def approve_facts(session: Session, payload: FactsApprovalRequest) -> FactsApprovalResponse:
    client = session.scalar(select(Client).where(
        Client.id == payload.client_id,
        Client.org_id == payload.org_id,
    ))
    if client is None:
        raise ApprovalError("client not found")

    run = PipelineRepository(session, payload.org_id).latest_for_client(client.id)
    if run is None or run.state != "FACTS_EXTRACTED":
        raise ApprovalError("client is not waiting for facts approval")

    facts = list(session.scalars(select(ClientFact).where(
        ClientFact.client_id == client.id,
        ClientFact.org_id == payload.org_id,
    ).order_by(ClientFact.key)))
    if not facts:
        raise ApprovalError("at least one fact is required before approval")

    snapshot = {
        "client_id": str(client.id),
        "facts": [{
            "key": fact.key,
            "value": fact.value,
            "value_type": fact.value_type,
            "source_kind": fact.source_kind,
            "source_ref": fact.source_ref,
            "confidence": fact.confidence,
        } for fact in facts],
    }
    artifact = Artifact(
        org_id=payload.org_id,
        artifact_type="business_facts",
        schema_version="1.0.0",
        payload_json=snapshot,
        revision=1,
        is_active=True,
    )
    ArtifactRepository(session, payload.org_id).add(artifact)

    for fact in facts:
        fact.status = "approved"
        fact.approved_by = payload.approved_by

    ApprovalRepository(session, payload.org_id).add(Approval(
        org_id=payload.org_id,
        artifact_id=artifact.id,
        gate="FACTS",
        decision="approved",
        feedback=payload.feedback,
        approved_by=payload.approved_by,
    ))

    next_state = transition(run.state, "FACTS_APPROVED").to_state
    run.state = next_state
    return FactsApprovalResponse(
        client_id=client.id,
        artifact_id=artifact.id,
        pipeline_run_id=run.id,
        state=next_state,
        approved_fact_count=len(facts),
    )
