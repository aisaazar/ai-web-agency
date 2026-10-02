"""Deterministic design selection and validation."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Artifact, ClientFact
from agency.domain.design_presets import (
    DEFAULT_DESIGN_PRESET_ID,
    SELECTED_PRESET_FACT_KEY,
    is_supported_design_preset,
)
from agency.repositories import ArtifactRepository, PipelineRepository
from agency.services.artifact_binding import belongs_to_client
from agency.services.pipeline_service import transition


class DesignError(ValueError):
    pass


def _client_selected_preset(session: Session, *, org_id, client_id) -> str | None:
    """The client's own intake selection, read through the tenant-scoped fact table.

    Scoped by ``org_id`` *and* ``client_id``, so another organization's client (or another client of
    the same organization) can never be read as this client's design intent. The approved selection
    wins over a proposal; a client that has not passed the facts gate yet still previews with the
    style that was chosen for it. Intake rejects duplicates, so a single row is the normal case.
    """
    facts = list(session.scalars(
        select(ClientFact)
        .where(
            ClientFact.org_id == org_id,
            ClientFact.client_id == client_id,
            ClientFact.key == SELECTED_PRESET_FACT_KEY,
        )
        .order_by(ClientFact.created_at.asc(), ClientFact.id.asc())
    ))
    if not facts:
        return None
    approved = [fact for fact in facts if fact.status == "approved"]
    return (approved or facts)[-1].value


def design_site(
    session: Session,
    *,
    org_id,
    client_id,
    content_artifact_id,
    preset_id: str | None = None,
    template_version: str = "1.0.0",
) -> Artifact:
    pipeline = PipelineRepository(session, org_id).latest_for_client(client_id)
    content = session.scalar(select(Artifact).where(
        Artifact.id == content_artifact_id,
        Artifact.org_id == org_id,
        Artifact.artifact_type == "content_model",
        Artifact.is_active.is_(True),
    ))
    if pipeline is None or pipeline.state != "CONTENT_APPROVED" or content is None:
        raise DesignError("content is not ready for design")
    if not belongs_to_client(session, org_id=org_id, artifact=content, client_id=client_id):
        raise DesignError("content artifact does not belong to client")

    if preset_id is None:
        # No style named in the request: the client's intake selection is the design intent, and the
        # historical default only applies to clients that never chose one.
        selected_preset_id = _client_selected_preset(
            session, org_id=org_id, client_id=client_id
        )
        if selected_preset_id is None:
            selected_preset_id = DEFAULT_DESIGN_PRESET_ID
    else:
        selected_preset_id = preset_id
    if not is_supported_design_preset(selected_preset_id):
        raise DesignError(f"unknown design preset: {selected_preset_id}")

    pipeline.state = transition(pipeline.state, "DESIGNING").to_state
    artifact = Artifact(
        org_id=org_id,
        artifact_type="design_plan",
        schema_version="1.0.0",
        payload_json={
            "client_id": str(client_id),
            "content_artifact_id": str(content.id),
            "template_version": template_version,
            "design_preset_id": selected_preset_id,
            "selection_mode": "deterministic",
        },
        revision=1,
        is_active=True,
    )
    ArtifactRepository(session, org_id).add(artifact)
    pipeline.state = transition(pipeline.state, "DESIGN_COMPLETE").to_state
    pipeline.state = transition(pipeline.state, "DESIGN_APPROVED").to_state
    return artifact
