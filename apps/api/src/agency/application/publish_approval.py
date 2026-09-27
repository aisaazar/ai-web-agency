"""Publish approval use case: binds the human gate to an immutable build artifact."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Approval, Artifact, Deploy
from agency.repositories import ApprovalRepository, PipelineRepository
from agency.services.audit_service import record_audit
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

    site_version_ref = artifact.payload_json.get("site_version_id")
    try:
        site_version_id = UUID(site_version_ref)
    except (TypeError, ValueError) as exc:
        raise PublishApprovalError("build artifact site_version_id is invalid") from exc

    preview_deploy = session.scalar(select(Deploy).where(
        Deploy.org_id == org_id,
        Deploy.site_version_id == site_version_id,
        Deploy.environment == "preview",
        Deploy.status == "preview_ready",
    ))
    if preview_deploy is None:
        raise PublishApprovalError("preview deployment not found for exact build")

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
    record_audit(
        session,
        org_id=org_id,
        actor=approved_by,
        action="approval.publish_approved",
        entity_type="artifact",
        entity_id=str(artifact.id),
        after={"gate": "PUBLISH", "decision": "approved", "client_id": str(client_id)},
    )
    return artifact
