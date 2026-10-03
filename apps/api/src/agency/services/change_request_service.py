"""Client review loop: change requests, immutable revisions, exact-build approval.

A change request pins the exact ``site_version_id`` / ``build_hash`` the client reviewed, so no
later approval or publish can silently attach to a different revision. A revision is a new content
artifact **revision**: the previous artifact row is never mutated, only flipped
``is_active=False``, while the change request keeps the lineage (request -> resulting content ->
resulting site version/build). Design, build, preview, approval and publish then reuse the existing
shared-template pipeline unchanged, which is also why the selected design preset survives the whole
loop: the revision carries the client's intake selection forward into the new content artifact.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from agency.db.models import Artifact, ChangeRequest, Client, Deploy, Site, SiteVersion
from agency.db.workflow_models import PipelineRun
from agency.repositories import ChangeRequestRepository, PipelineRepository
from agency.services.artifact_binding import belongs_to_client
from agency.services.audit_service import record_audit
from agency.services.pipeline_service import transition


class ChangeRequestError(ValueError):
    """Raised when a review-loop request cannot be applied."""


REVISIONABLE_STATES = frozenset({"PREVIEW_READY"})

REVIEW_DECISIONS = frozenset({"resolved", "rejected"})


def _client(session: Session, *, org_id, client_id) -> Client:
    client = session.scalar(select(Client).where(Client.id == client_id, Client.org_id == org_id))
    if client is None:
        raise ChangeRequestError("client not found")
    return client


def _pipeline(session: Session, *, org_id, client_id) -> PipelineRun:
    pipeline = PipelineRepository(session, org_id).latest_for_client(client_id)
    if pipeline is None:
        raise ChangeRequestError("client has no pipeline run")
    return pipeline


def _reviewed_version(session: Session, *, org_id, client_id, site_version_id) -> SiteVersion:
    """The exact site version under review: org-scoped, client-bound, currently built."""
    version = session.scalar(select(SiteVersion).where(
        SiteVersion.id == site_version_id,
        SiteVersion.org_id == org_id,
    ))
    if version is None:
        raise ChangeRequestError("site version not found")
    site = session.scalar(select(Site).where(
        Site.id == version.site_id,
        Site.org_id == org_id,
        Site.client_id == client_id,
    ))
    if site is None:
        raise ChangeRequestError("site version does not belong to client")
    pipeline = _pipeline(session, org_id=org_id, client_id=client_id)
    if pipeline.state not in REVISIONABLE_STATES:
        raise ChangeRequestError(f"client is not in review (state {pipeline.state})")
    if site.current_build_hash != version.build_hash:
        raise ChangeRequestError("site version is not the current build for this client")
    return version


def _preview_ready_for_version(session: Session, *, org_id, version: SiteVersion) -> Deploy:
    preview = session.scalar(select(Deploy).where(
        Deploy.org_id == org_id,
        Deploy.site_version_id == version.id,
        Deploy.environment == "preview",
        Deploy.status == "preview_ready",
    ).order_by(Deploy.created_at.desc()))
    if preview is None:
        raise ChangeRequestError("reviewed preview deployment not found for site version")
    return preview


def _get_request(session: Session, *, org_id, client_id, change_request_id) -> ChangeRequest:
    change_request = ChangeRequestRepository(session, org_id).get(change_request_id)
    # `Client.id` is a SQLAlchemy `Uuid` column, so the loaded attribute is a `uuid.UUID` even though
    # the model is annotated as `str`. Comparing it to `str(client_id)` therefore never matches and
    # every follow-up call on a change request failed as "not found". Normalise both sides.
    if change_request is None or str(change_request.client_id) != str(client_id):
        raise ChangeRequestError("change request not found for client")
    return change_request


def _artifact_revisions_for_client(session: Session, *, org_id, client_id, artifact_type: str):
    """Newest-first artifacts of one type provably belonging to one client."""
    candidates = list(session.scalars(select(Artifact).where(
        Artifact.org_id == org_id,
        Artifact.artifact_type == artifact_type,
        Artifact.is_active.is_(True),
    ).order_by(Artifact.created_at.desc(), Artifact.revision.desc())))
    return [
        artifact for artifact in candidates
        if belongs_to_client(session, org_id=org_id, artifact=artifact, client_id=client_id)
    ]


def _next_revision_number(session: Session, *, org_id) -> int:
    """Derive the next content-model revision from the DB via func.max."""
    max_revision = session.scalar(
        select(func.max(Artifact.revision)).where(
            Artifact.org_id == org_id,
            Artifact.artifact_type == "content_model",
        )
    )
    return (max_revision or 0) + 1


def create_change_request(
    session: Session,
    *,
    org_id,
    client_id,
    site_version_id,
    requested_by,
    body,
) -> ChangeRequest:
    _client(session, org_id=org_id, client_id=client_id)
    version = _reviewed_version(
        session, org_id=org_id, client_id=client_id, site_version_id=site_version_id
    )
    _preview_ready_for_version(session, org_id=org_id, version=version)

    change_request = ChangeRequest(
        org_id=org_id,
        client_id=client_id,
        site_id=version.site_id,
        site_version_id=version.id,
        build_hash=version.build_hash,
        requested_by=requested_by,
        body=body,
        status="open",
    )
    ChangeRequestRepository(session, org_id).add(change_request)
    record_audit(
        session,
        org_id=org_id,
        actor=requested_by,
        action="review.change_requested",
        entity_type="change_request",
        entity_id=str(change_request.id),
        after={
            "client_id": str(client_id),
            "site_version_id": str(version.id),
                    "build_hash": version.build_hash,
        },
    )
    return change_request


def _open_request_for_revision(
    session: Session, *, org_id, client_id, change_request_id
):
    """The open request plus the live state its revision must be built on."""
    _client(session, org_id=org_id, client_id=client_id)
    pipeline = _pipeline(session, org_id=org_id, client_id=client_id)
    change_request = _get_request(
        session, org_id=org_id, client_id=client_id, change_request_id=change_request_id
    )
    if change_request.status != "open":
        raise ChangeRequestError(f"change request is {change_request.status}")
    if pipeline.state not in REVISIONABLE_STATES:
        raise ChangeRequestError(f"client is not in review (state {pipeline.state})")
    version = _reviewed_version(
        session,
        org_id=org_id,
        client_id=client_id,
        site_version_id=change_request.site_version_id,
    )
    if version.id != change_request.site_version_id:
        raise ChangeRequestError("change request no longer points at the current build")
    current = _artifact_revisions_for_client(
        session, org_id=org_id, client_id=client_id, artifact_type="content_model"
    )
    if not current:
        raise ChangeRequestError("no content revision found for client")
    return change_request, pipeline, current[0]


def _mark_revision_started(
    session: Session, *, org_id, change_request, revision, actor
) -> None:
    change_request.status = "in_progress"
    change_request.resulting_content_artifact_id = revision.id
    record_audit(
        session,
        org_id=org_id,
        actor=actor,
        action="review.revision_started",
        entity_type="change_request",
        entity_id=str(change_request.id),
        after={
            "client_id": str(change_request.client_id),
            "content_artifact_id": str(revision.id),
            "revision": revision.revision,
        },
    )


def start_revision(
    session: Session,
    *,
    org_id,
    client_id,
    change_request_id,
    content,
    approved_by,
) -> Artifact:
    """Create the next immutable content revision from caller-supplied content.

    Only the content step runs here: the standard CONTENT approval, design, build and preview
    actions then take the revision through the gates that already exist, so no gate is bypassed.
    """
    from agency.services.content_service import ContentGenerationError, generate_content

    change_request, pipeline, source = _open_request_for_revision(
        session, org_id=org_id, client_id=client_id, change_request_id=change_request_id
    )
    pipeline.state = transition(pipeline.state, "CONTENT_GENERATING").to_state
    try:
        revision = generate_content(
            session,
            org_id=org_id,
            client_id=client_id,
            payload={
                **{key: value for key, value in source.payload_json.items()},
                **content,
            },
            revision_number=_next_revision_number(session, org_id=org_id),
            archive_previous=source,
        )
    except ContentGenerationError as exc:
        pipeline.state = transition(pipeline.state, "FAILED").to_state
        raise ChangeRequestError(str(exc)) from exc
    _mark_revision_started(
        session, org_id=org_id, change_request=change_request, revision=revision, actor=approved_by
        )
    return revision


def start_llm_revision(
    session: Session,
    *,
    org_id,
    client_id,
    change_request_id,
    instruction=None,
    provider_name=None,
    approved_by,
) -> Artifact:
    """LLM-backed variant of :func:`start_revision` for dashboard-driven revisions."""
    from agency.services.content_ai_service import (
        AIContentGenerationError,
        generate_content_with_llm,
    )

    change_request, pipeline, source = _open_request_for_revision(
        session, org_id=org_id, client_id=client_id, change_request_id=change_request_id
    )
    pipeline.state = transition(pipeline.state, "CONTENT_GENERATING").to_state
    try:
        revision = generate_content_with_llm(
            session,
            org_id=org_id,
            client_id=client_id,
            instruction=instruction or change_request.body,
            provider_name=provider_name,
            revision_number=_next_revision_number(session, org_id=org_id),
            archive_previous=source,
        )
    except AIContentGenerationError as exc:
        pipeline.state = transition(pipeline.state, "FAILED").to_state
        raise ChangeRequestError(str(exc)) from exc
    _mark_revision_started(
        session, org_id=org_id, change_request=change_request, revision=revision, actor=approved_by
    )
    return revision


def resolve_change_request(
    session: Session,
    *,
    org_id,
    client_id,
    change_request_id,
    site_version_id,
    build_hash,
    approved_by,
    decision: str = "resolved",
) -> ChangeRequest:
    """Pin the resulting build hash to the change request and close it."""
    if decision not in REVIEW_DECISIONS:
        raise ChangeRequestError(f"invalid decision: {decision}")
    _client(session, org_id=org_id, client_id=client_id)
    pipeline = _pipeline(session, org_id=org_id, client_id=client_id)
    if pipeline.state != "PREVIEW_READY":
        raise ChangeRequestError(
            f"client must complete design/build/preview before resolving "
            f"(state {pipeline.state})"
        )
    change_request = _get_request(
        session, org_id=org_id, client_id=client_id, change_request_id=change_request_id
    )
    if change_request.status != "in_progress":
        raise ChangeRequestError(f"change request is {change_request.status}")
    version = session.scalar(select(SiteVersion).where(
        SiteVersion.id == site_version_id,
        SiteVersion.org_id == org_id,
    ))
    if version is None:
        raise ChangeRequestError("resulting site version not found")
    site = session.scalar(select(Site).where(
        Site.id == version.site_id,
        Site.org_id == org_id,
        Site.client_id == client_id,
    ))
    if site is None:
        raise ChangeRequestError("resulting site version does not belong to client")
    if version.build_hash != build_hash:
        raise ChangeRequestError("build_hash does not match site version")
    if change_request.resulting_content_artifact_id is None:
        raise ChangeRequestError("change request has no resulting content artifact")
    if version.content_artifact_id != change_request.resulting_content_artifact_id:
        raise ChangeRequestError(
            "resulting site version content_artifact_id does not match the revision"
        )
    change_request.status = decision
    change_request.resulting_build_hash = build_hash
    record_audit(
        session,
        org_id=org_id,
        actor=approved_by,
        action=f"review.change_request_{decision}",
        entity_type="change_request",
        entity_id=str(change_request.id),
        after={
            "client_id": str(client_id),
            "resulting_build_hash": build_hash,
            "resulting_content_artifact_id": str(change_request.resulting_content_artifact_id),
        },
    )
    return change_request