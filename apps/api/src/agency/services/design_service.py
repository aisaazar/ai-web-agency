"""Deterministic design selection and validation."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Artifact
from agency.repositories import ArtifactRepository, PipelineRepository
from agency.services.artifact_binding import belongs_to_client
from agency.services.pipeline_service import transition


class DesignError(ValueError):
    pass


def design_site(session: Session, *, org_id, client_id, content_artifact_id, preset_id: str = "health", template_version: str = "1.0.0") -> Artifact:
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
    if preset_id not in {"health"}:
        raise DesignError(f"unknown design preset: {preset_id}")

    pipeline.state = transition(pipeline.state, "DESIGNING").to_state
    artifact = Artifact(
        org_id=org_id,
        artifact_type="design_plan",
        schema_version="1.0.0",
        payload_json={
            "client_id": str(client_id),
            "content_artifact_id": str(content.id),
            "template_version": template_version,
            "design_preset_id": preset_id,
            "selection_mode": "deterministic",
        },
        revision=1,
        is_active=True,
    )
    ArtifactRepository(session, org_id).add(artifact)
    pipeline.state = transition(pipeline.state, "DESIGN_COMPLETE").to_state
    pipeline.state = transition(pipeline.state, "DESIGN_APPROVED").to_state
    return artifact
