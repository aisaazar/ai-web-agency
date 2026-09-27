"""Publish approval use case: binds the human gate to an immutable build artifact."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Approval, Artifact
from agency.repositories import ApprovalRepository, PipelineRepository
from agency.services.pipeline_service import transition


class PublishApprovalError(ValueError):
    pass


def approve_publish(
    session: Session,
    *,
    org_id,
    client_id,
    build_artifact_id,
    approved_by,
    feedback=None,
) -> Artifact:
    pipeline = PipelineRepository(session, org_id).latest_for_client(client_id)
    artifact = session.scalar(select(Artifact).where(
        Artifact.id == build_artifact_id,
        Artifact.org_id == org_id,
        Artifact.artifact_type == "site_build",
        Artifact.is_active.is_(True),
    ))
    if pipeline is None or pipeline.state != "PREVIEW_READY" or artifact is None:
        raise PublishApprovalError("preview is not ready for approval")

    if artifact.payload_json.get("client_id") != str(client_id):
        raise PublishApprovalError("build artifact does not belong to client")

    if not artifact.build_hash or artifact.payload_json.get("build_hash") != artifact.build_hash:
        raise PublishApprovalError("build artifact hash is missing or inconsistent")

    existing = ApprovalRepository(session, org_id).for_artifact(artifact.id)
    if any(item.gate == "PUBLISH" and item.decision == "approved" for item in existing):
        raise PublishApprovalError("build artifact is already publish-approved")

    ApprovalRepository(session, org_id).add(Approval(
        org_id=org_id,
        artifact_id=artifact.id,
        gate="PUBLISH",
        decision="approved",
        feedback=feedback,
        approved_by=approved_by,
    ))
    pipeline.state = transition(pipeline.state, "PREVIEW_APPROVED").to_state
    return artifact
