"""Intake use case: create tenant-scoped client facts and workflow state."""

from sqlalchemy.orm import Session

from agency.api.intake_schemas import IntakeRequest, IntakeResponse
from agency.db.models import Client, ClientFact
from agency.db.workflow_models import PipelineRun
from agency.repositories import ClientFactRepository, ClientRepository, PipelineRepository
from agency.services.pipeline_service import transition


class IntakeError(ValueError):
    """Raised for an invalid intake request."""


def submit_intake(session: Session, payload: IntakeRequest) -> IntakeResponse:
    clients = ClientRepository(session, payload.org_id)
    if clients.get_by_slug(payload.client_slug) is not None:
        raise IntakeError("client slug already exists in this organization")

    client = Client(
        org_id=payload.org_id,
        name=payload.client_name.strip(),
        slug=payload.client_slug,
        category=payload.category.strip(),
        jurisdiction=payload.jurisdiction,
        locale=payload.locale,
        existing_url=payload.existing_url,
    )
    clients.add(client)

    facts = ClientFactRepository(session, payload.org_id)
    for item in payload.facts:
        facts.add(ClientFact(
            org_id=payload.org_id,
            client_id=client.id,
            key=item.key,
            value=item.value,
            value_type=item.value_type,
            source_kind=item.source_kind,
            source_ref=item.source_ref,
            confidence=item.confidence,
            status="proposed",
        ))

    state = transition("INTAKE", "FACTS_EXTRACTED").to_state
    run = PipelineRun(org_id=payload.org_id, client_id=client.id, state=state)
    PipelineRepository(session, payload.org_id).add(run)
    return IntakeResponse(client_id=client.id, pipeline_run_id=run.id, state=state, fact_count=len(payload.facts))
