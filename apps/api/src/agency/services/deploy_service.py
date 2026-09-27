"""Deployment use case with exact-build validation and provider isolation."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Approval, Artifact, BuildValidation, Deploy, Site, SiteVersion
from agency.domain.pipeline_definition import is_valid_transition
from agency.providers.deploy import BuildBundle, DeploymentProvider
from agency.providers.deployment_registry import get_deployment_provider
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


BUILD_BUNDLES_ROOT = Path(__file__).resolve().parents[5] / ".artifacts" / "builds"


def _default_provider() -> DeploymentProvider:
    return get_deployment_provider("local_static")


def _bundle_for_version(version: SiteVersion) -> BuildBundle:
    output_dir = BUILD_BUNDLES_ROOT / version.build_hash
    if not output_dir.is_dir():
        raise DeployError(f"immutable build bundle not found for build_hash {version.build_hash}")
    return BuildBundle(build_hash=version.build_hash, output_dir=output_dir)


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


def create_preview(
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
    if site is None or pipeline is None or pipeline.state != "PREVIEW_READY":
        raise DeployError("site is not ready for preview deployment")

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

    existing = session.scalar(select(Deploy).where(
        Deploy.org_id == org_id,
        Deploy.site_version_id == version.id,
        Deploy.environment == "preview",
        Deploy.status == "preview_ready",
    ))
    if existing is not None:
        return existing

    deployer = provider or _default_provider()
    preview = deployer.create_preview(_bundle_for_version(version))
    record = Deploy(
        org_id=org_id,
        site_version_id=version.id,
        environment="preview",
        provider=preview.provider,
        status=preview.status,
        url=preview.url,
    )
    session.add(record)
    session.flush()
    return record


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

    preview_deploy = session.scalar(select(Deploy).where(
        Deploy.org_id == org_id,
        Deploy.site_version_id == version.id,
        Deploy.environment == "preview",
        Deploy.status == "preview_ready",
    ))
    if preview_deploy is None:
        raise DeployError("preview deployment not found for exact build")

    deployer = provider or get_deployment_provider(preview_deploy.provider)
    if deployer.name != preview_deploy.provider:
        raise DeployError("deployment provider does not match approved preview")
    promoted = deployer.promote(version.build_hash)

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


def rollback_site(
    session: Session,
    *,
    org_id,
    client_id,
    build_hash: str,
    provider: DeploymentProvider | None = None,
) -> Deploy:
    current_site = session.scalar(select(Site).where(
        Site.org_id == org_id,
        Site.client_id == client_id,
    ))
    if current_site is None:
        raise DeployError("site not found")

    live_deploy = session.scalar(select(Deploy).where(
        Deploy.org_id == org_id,
        Deploy.site_version_id.in_(
            select(SiteVersion.id).where(SiteVersion.site_id == current_site.id)
        ),
        Deploy.environment == "production",
        Deploy.status == "live",
    ).order_by(Deploy.created_at.desc()))
    if live_deploy is None:
        raise DeployError("site has no live deployment to roll back")

    target_version = session.scalar(select(SiteVersion).where(
        SiteVersion.org_id == org_id,
        SiteVersion.site_id == current_site.id,
        SiteVersion.build_hash == build_hash,
    ))
    if target_version is None:
        raise DeployError("target build_hash is not a site version for this client")

    _assert_validations(
        session,
        org_id=org_id,
        site_version_id=target_version.id,
        build_hash=target_version.build_hash,
    )

    target_artifact = session.scalar(select(Artifact).where(
        Artifact.org_id == org_id,
        Artifact.artifact_type == "site_build",
        Artifact.build_hash == target_version.build_hash,
        Artifact.is_active.is_(True),
    ))
    if target_artifact is None:
        raise DeployError("target site build artifact not found")

    approved = session.scalar(select(Approval).where(
        Approval.org_id == org_id,
        Approval.artifact_id == target_artifact.id,
        Approval.gate == "PUBLISH",
        Approval.decision == "approved",
    ))
    if approved is None:
        raise DeployError("target build has no publish approval")

    deployer = provider or get_deployment_provider(live_deploy.provider)
    if deployer.name != live_deploy.provider:
        raise DeployError("deployment provider does not match live deployment")

    promoted = deployer.rollback(str(current_site.id), target_version.build_hash)
    record = Deploy(
        org_id=org_id,
        site_version_id=target_version.id,
        environment="production",
        provider=promoted.provider,
        status=promoted.status,
        url=promoted.url,
    )
    session.add(record)
    session.flush()

    current_site.current_build_hash = target_version.build_hash
    current_site.live_url = promoted.url
    current_site.status = "live"
    return record
