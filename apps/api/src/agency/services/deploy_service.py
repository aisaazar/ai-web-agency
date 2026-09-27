"""Deployment use case with exact-build validation and provider isolation."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Approval, Artifact, BuildValidation, Deploy, Site, SiteVersion
from agency.domain.pipeline_definition import is_valid_transition
from agency.providers.deploy import BuildBundle, DeploymentProvider, LocalStaticDeploymentProvider
from agency.repositories import PipelineRepository
from agency.services.pipeline_service import transition

REQUIRED_VALIDATION_CHECKS = frozenset({
    "content_schema",
    "facts_provenance",
    "claims_policy",
    "required_legal_pages",
    "typecheck",
    "next_build",
    "linkcheck",
    "a11y_budget",
    "perf_budget",
    "playwright_smoke",
    "seo_manifest",
})


class DeployError(RuntimeError):
    pass


def _default_provider() -> DeploymentProvider:
    return LocalStaticDeploymentProvider(
        dist_root=Path(__file__).resolve().parents[5] / ".artifacts" / "deploys"
    )


def _assert_validations(session: Session, *, org_id, site_version_id, build_hash: str) -> None:
    rows = list(session.scalars(select(BuildValidation).where(
        BuildValidation.org_id == org_id,
        BuildValidation.site_version_id == site_version_id,
    )))
    by_name = {row.check_name: row for row in rows}
    missing = REQUIRED_VALIDATION_CHECKS - by_name.keys()
    failed = {name for name in REQUIRED_VALIDATION_CHECKS if name in by_name and not by_name[name].passed}
    if missing or failed:
        reasons = []
        if missing:
            reasons.append("missing=" + ",".join(sorted(missing)))
        if failed:
            reasons.append("failed=" + ",".join(sorted(failed)))
        raise DeployError(
            "deployment gate failed for build_hash "
            + build_hash
            + ": "
            + "; ".join(reasons)
        )


def publish_site(
    session: Session,
    *,
    org_id,
    client_id,
    site_version_id,
    provider: DeploymentProvider | None = None,
) -> Deploy:
    version = session.scalar(select(SiteVersion).where(
        SiteVersion.id == site_version_id,
        SiteVersion.org_id == org_id,
    ))
    if version is None:
        raise DeployError("site version not found")

    site = session.scalar(select(Site).where(
        Site.id == version.site_id,
        Site.org_id == org_id,
        Site.client_id == client_id,
    ))
    pipeline = PipelineRepository(session, org_id).latest_for_client(client_id)
    if site is None or pipeline is None or pipeline.state != "PREVIEW_APPROVED":
        raise DeployError("site is not ready to publish")

    _assert_validations(
        session,
        org_id=org_id,
        site_version_id=version.id,
        build_hash=version.build_hash,
    )

    build_artifact = session.scalar(select(Artifact).where(
        Artifact.org_id == org_id,
        Artifact.artifact_type == "site_build",
        Artifact.build_hash == version.build_hash,
        Artifact.input_artifact_id == version.content_artifact_id,
        Artifact.is_active.is_(True),
    ))
    if build_artifact is None:
        raise DeployError("site build artifact not found for exact build_hash")

    publish_approval = session.scalar(select(Approval).where(
        Approval.org_id == org_id,
        Approval.artifact_id == build_artifact.id,
        Approval.gate == "PUBLISH",
        Approval.decision == "approved",
    ))
    if publish_approval is None:
        raise DeployError("publish approval not found for exact build artifact")

    deployer = provider or _default_provider()
    bundle = BuildBundle(
        build_hash=version.build_hash,
        output_dir=Path(__file__).resolve().parents[5] / "sites" / "_template-base" / "out",
    )
    preview = deployer.create_preview(bundle)
    promoted = deployer.promote(preview.deploy_ref)

    record = Deploy(
        org_id=org_id,
        site_version_id=version.id,
        environment="production",
        provider=promoted.provider,
        status=promoted.status,
        url=promoted.url,
    )
    session.add(record)
    session.flush()

    if not is_valid_transition(pipeline.state, "PUBLISHING"):
        raise DeployError(f"cannot publish from state {pipeline.state}")
    pipeline.state = transition(pipeline.state, "PUBLISHING").to_state
    pipeline.state = transition(pipeline.state, "LIVE").to_state
    site.current_build_hash = version.build_hash
    site.live_url = promoted.url
    site.status = "live"
    return record
