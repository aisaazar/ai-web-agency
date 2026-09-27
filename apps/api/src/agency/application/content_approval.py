"""Content approval use case."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Approval, Artifact
from agency.repositories import ApprovalRepository, PipelineRepository
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
    ApprovalRepository(session, org_id).add(Approval(
        org_id=org_id,
        artifact_id=artifact.id,
        gate="CONTENT",
        decision="approved",
        feedback=feedback,
        approved_by=approved_by,
    ))
    pipeline.state = transition(pipeline.state, "CONTENT_APPROVED").to_state
    return artifact
