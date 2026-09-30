"""Content approval use case."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Approval, Artifact
from agency.repositories import ApprovalRepository, PipelineRepository
from agency.services.artifact_binding import belongs_to_client
from agency.services.audit_service import record_audit
from agency.services.pipeline_service import transition


class ContentApprovalError(ValueError):
    pass


def approve_content(session: Session, *, org_id, client_id, artifact_id, approved_by, feedback=None) -> Artifact:
    pipeline = PipelineRepository(session, org_id).latest_for_client(client_id)
    artifact = session.scalar(select(Artifact).where(
        Artifact.id == artifact_id,
        Artifact.org_id == org_id,
        Artifact.artifact_type == "content_model",
        Artifact.is_active.is_(True),
    ))
    if pipeline is None or pipeline.state != "CONTENT_COMPLETE" or artifact is None:
        raise ContentApprovalError("content is not ready for approval")
    if not belongs_to_client(session, org_id=org_id, artifact=artifact, client_id=client_id):
        raise ContentApprovalError("content artifact does not belong to client")
    ApprovalRepository(session, org_id).add(Approval(
        org_id=org_id,
        artifact_id=artifact.id,
        gate="CONTENT",
        decision="approved",
        feedback=feedback,
        approved_by=approved_by,
    ))
    pipeline.state = transition(pipeline.state, "CONTENT_APPROVED").to_state
    record_audit(
        session,
        org_id=org_id,
        actor=approved_by,
        action="approval.content_approved",
        entity_type="artifact",
        entity_id=str(artifact.id),
        after={"gate": "CONTENT", "decision": "approved", "client_id": str(client_id)},
    )
    return artifact
