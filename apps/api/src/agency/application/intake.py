"""Intake use case: create tenant-scoped client facts and workflow state."""

from sqlalchemy.orm import Session

from agency.api.intake_schemas import IntakeFactIn, IntakeRequest, IntakeResponse
from agency.db.models import Client, ClientFact
from agency.db.workflow_models import PipelineRun
from agency.domain.design_presets import (
    SELECTED_PRESET_FACT_KEY,
    SUPPORTED_DESIGN_PRESET_IDS,
    is_supported_design_preset,
)
from agency.repositories import ClientFactRepository, ClientRepository, PipelineRepository
from agency.services.pipeline_service import transition


class IntakeError(ValueError):
    """Raised for an invalid intake request."""


def _validate_preset_selection(facts: list[IntakeFactIn]) -> None:
    """Reject an unusable gallery selection before anything is written for this organization.

    The selection is stored as an ordinary intake fact so no schema change is needed, but the one
    fact the design stage depends on must be unambiguous: an unsupported value would otherwise reach
    the design service, and a repeated key would make the "selected" preset depend on row order.
    """
    selections = [item for item in facts if item.key == SELECTED_PRESET_FACT_KEY]
    if len(selections) > 1:
        raise IntakeError(f"{SELECTED_PRESET_FACT_KEY} must be provided at most once per client")
    for item in selections:
        if not is_supported_design_preset(item.value):
            supported = ", ".join(SUPPORTED_DESIGN_PRESET_IDS)
            raise IntakeError(
                f"unsupported {SELECTED_PRESET_FACT_KEY}: {item.value} (supported: {supported})"
            )


def submit_intake(session: Session, payload: IntakeRequest) -> IntakeResponse:
    _validate_preset_selection(payload.facts)

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
