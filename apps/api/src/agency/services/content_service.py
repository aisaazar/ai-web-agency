"""Content-generation boundary with strict schema and claims validation."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Artifact, Client, ClientFact
from agency.db.workflow_models import PipelineRun
from agency.domain.claims_policy import assert_claims_allowed
from agency.domain.content_model import ContentModel
from agency.repositories import ArtifactRepository, PipelineRepository
from agency.services.pipeline_service import transition


class ContentGenerationError(ValueError):
    """Raised when content cannot be safely generated from approved facts."""


def _strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in _strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _strings(child)]
    return []


def generate_content(
    session: Session,
    *,
    org_id,
    client_id,
    payload: dict,
    revision_number: int = 1,
    archive_previous: Artifact | None = None,
) -> Artifact:
    client = session.scalar(select(Client).where(Client.id == client_id, Client.org_id == org_id))
    if client is None:
        raise ContentGenerationError("client not found")
    pipeline = PipelineRepository(session, org_id).latest_for_client(client.id)
    if pipeline is None or pipeline.state not in {"RESEARCH_APPROVED", "CONTENT_GENERATING"}:
        raise ContentGenerationError("client is not ready for content generation")

    approved_fact_keys = set(session.scalars(select(ClientFact.key).where(
        ClientFact.org_id == org_id,
        ClientFact.client_id == client.id,
        ClientFact.status == "approved",
    )))
    declared_fact_keys = set(payload.get("_fact_keys", []))
    if declared_fact_keys - approved_fact_keys:
        raise ContentGenerationError("content references unapproved facts")
    content_payload = {key: value for key, value in payload.items() if key != "_fact_keys"}

    try:
        validated = ContentModel.model_validate(content_payload)
        assert_claims_allowed(_strings(content_payload))
    except ValueError as exc:
        raise ContentGenerationError(str(exc)) from exc

    facts_artifacts = list(session.scalars(select(Artifact).where(
        Artifact.org_id == org_id,
        Artifact.artifact_type == "business_facts",
        Artifact.is_active.is_(True),
    ).order_by(Artifact.created_at.desc())))
    facts_artifact = next(
        (artifact for artifact in facts_artifacts
         if artifact.payload_json.get("client_id") == str(client_id)),
        None,
    )
    if facts_artifact is None:
        raise ContentGenerationError("approved facts artifact not found for client")

    if pipeline.state == "RESEARCH_APPROVED":
        pipeline.state = transition(pipeline.state, "CONTENT_GENERATING").to_state
    if archive_previous is not None and archive_previous.is_active:
        stored = session.get(Artifact, archive_previous.id)
        if stored is not None and stored.is_active:
            stored.is_active = False
            session.flush()
    artifact = Artifact(
        org_id=org_id,
        artifact_type="content_model",
        schema_version=validated.content_schema_version,
        payload_json=validated.model_dump(mode="json"),
        revision=revision_number,
        input_artifact_id=facts_artifact.id,
        is_active=True,
    )
    ArtifactRepository(session, org_id).add(artifact)
    pipeline.state = transition(pipeline.state, "CONTENT_COMPLETE").to_state
    return artifact
