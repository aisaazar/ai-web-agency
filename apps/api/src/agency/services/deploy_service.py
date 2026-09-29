"""Deployment use case with exact-build validation and provider isolation."""
from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Approval, Artifact, BuildValidation, Deploy, Site, SiteVersion
from agency.domain.pipeline_definition import is_valid_transition
from agency.providers.deploy import BuildBundle, DeploymentProvider, DomainResult
from agency.providers.deployment_registry import get_deployment_provider
from agency.repositories import PipelineRepository
from agency.services.audit_service import record_audit
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


def _as_deploy_error(label: str, call):
    """Turn a provider/network/filesystem failure into an actionable DeployError.

    Provider boundaries are the only place where an unexpected exception type is expected: a missing
    credential, a rejected upload or a dead endpoint must reach the operator as a diagnosis, not as an
    opaque HTTP 500.
    """
    try:
        return call()
    except DeployError:
        raise
    except Exception as exc:
        raise DeployError(f"{label} failed: {exc}") from exc


_FQDN_PATTERN = re.compile(r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\Z")


def _normalize_fqdn(value: str) -> str:
    """One canonical spelling of the client's domain, rejected before any provider call."""
    fqdn = (value or "").strip().lower().rstrip(".")
    if "://" in fqdn or "/" in fqdn or "@" in fqdn or _FQDN_PATTERN.fullmatch(fqdn) is None:
        raise DeployError("fqdn must be a valid DNS hostname without scheme or path")
    return fqdn


def _assert_exact_build_artifact(*, artifact: Artifact, client_id, version: SiteVersion) -> Artifact:
    payload = artifact.payload_json
    if payload.get("client_id") != str(client_id):
        raise DeployError("site build artifact client binding is inconsistent")
    if payload.get("site_version_id") != str(version.id):
        raise DeployError("site build artifact site_version binding is inconsistent")
    if payload.get("build_hash") != version.build_hash or artifact.build_hash != version.build_hash:
        raise DeployError("site build artifact build_hash binding is inconsistent")
    if artifact.input_artifact_id != version.content_artifact_id:
        raise DeployError("site build artifact input binding is inconsistent")
    return artifact


def _published_build_artifact(session: Session, *, org_id, client_id, version: SiteVersion) -> Artifact:
    """The exact immutable build artifact of a site version, plus its binding publish approval."""
    artifact = session.scalar(select(Artifact).where(
        Artifact.org_id == org_id,
        Artifact.artifact_type == "site_build",
        Artifact.build_hash == version.build_hash,
        Artifact.input_artifact_id == version.content_artifact_id,
        Artifact.is_active.is_(True),
    ))
    if artifact is None:
        raise DeployError("site build artifact not found for exact build_hash")
    _assert_exact_build_artifact(artifact=artifact, client_id=client_id, version=version)
    approved = session.scalar(select(Approval).where(
        Approval.org_id == org_id,
        Approval.artifact_id == artifact.id,
        Approval.gate == "PUBLISH",
        Approval.decision == "approved",
    ))
    if approved is None:
        raise DeployError("publish approval not found for exact build artifact")
    return artifact


def _live_deploy(session: Session, *, org_id, site_id) -> Deploy | None:
    return session.scalar(select(Deploy).where(
        Deploy.org_id == org_id,
        Deploy.site_version_id.in_(
            select(SiteVersion.id).where(SiteVersion.site_id == site_id)
        ),
        Deploy.environment == "production",
        Deploy.status == "live",
    ).order_by(Deploy.created_at.desc()))


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
    if site.current_build_hash != version.build_hash:
        raise DeployError("site version is not the current build for this client")

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
    _assert_exact_build_artifact(artifact=build_artifact, client_id=client_id, version=version)

    deployer = provider or _default_provider()
    existing = session.scalar(select(Deploy).where(
        Deploy.org_id == org_id,
        Deploy.site_version_id == version.id,
        Deploy.environment == "preview",
        Deploy.status == "preview_ready",
    ))
    if existing is not None:
        if existing.provider != deployer.name:
            raise DeployError(
                f"existing preview provider {existing.provider!r} does not match requested provider {deployer.name!r}"
            )
        return existing

    preview = _as_deploy_error(
        "preview deployment", lambda: deployer.create_preview(_bundle_for_version(version))
    )
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
    record_audit(
        session,
        org_id=org_id,
        actor="system",
        action="deployment.preview_created",
        entity_type="deploy",
        entity_id=str(record.id),
        after={"client_id": str(client_id), "build_hash": version.build_hash, "url": record.url},
    )
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
    if site.current_build_hash != version.build_hash:
        raise DeployError("site version is not the current build for this client")

    _assert_validations(
        session,
        org_id=org_id,
        site_version_id=version.id,
        build_hash=version.build_hash,
    )

    build_artifact = _published_build_artifact(
        session, org_id=org_id, client_id=client_id, version=version
    )

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
    promote_ref = (
        preview_deploy.url
        if deployer.name == "vercel" and preview_deploy.url
        else version.build_hash
    )
    promoted = _as_deploy_error("publish", lambda: deployer.promote(promote_ref))

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
    record_audit(
        session,
        org_id=org_id,
        actor="system",
        action="deployment.published",
        entity_type="deploy",
        entity_id=str(record.id),
        after={"client_id": str(client_id), "build_hash": version.build_hash, "url": record.url},
    )
    return record


def attach_domain(
    session: Session,
    *,
    org_id,
    client_id,
    fqdn: str,
    provider: DeploymentProvider | None = None,
) -> DomainResult:
    site = session.scalar(select(Site).where(
        Site.org_id == org_id,
        Site.client_id == client_id,
    ))
    if site is None:
        raise DeployError("site not found")
    live = _live_deploy(session, org_id=org_id, site_id=site.id)
    if live is None:
        raise DeployError("site must have a live deployment before attaching a domain")
    deployer = provider or get_deployment_provider(live.provider)
    if deployer.name != live.provider:
        raise DeployError("deployment provider does not match live deployment")
    normalized = _normalize_fqdn(fqdn)
    return _as_deploy_error(
        "domain attachment", lambda: deployer.attach_domain(str(site.id), normalized)
    )


def deployment_logs(
    session: Session,
    *,
    org_id,
    client_id,
    deploy_id,
    provider: DeploymentProvider | None = None,
) -> str:
    deploy = session.scalar(select(Deploy).where(
        Deploy.id == deploy_id,
        Deploy.org_id == org_id,
    ))
    if deploy is None:
        raise DeployError("deployment not found")
    site = session.scalar(select(Site).join(
        SiteVersion, SiteVersion.site_id == Site.id
    ).where(
        SiteVersion.id == deploy.site_version_id,
        Site.org_id == org_id,
        Site.client_id == client_id,
    ))
    if site is None:
        raise DeployError("deployment does not belong to this client")
    deployer = provider or get_deployment_provider(deploy.provider)
    if deployer.name != deploy.provider:
        raise DeployError("deployment provider does not match stored deployment")
    deploy_ref = deploy.url or ""
    if deploy.provider == "local_static":
        deploy_ref = Path(deploy.url.removeprefix("file:///")).parent.name if deploy.url else ""
    if not deploy_ref:
        raise DeployError("deployment has no provider reference")
    return _as_deploy_error("deployment logs", lambda: deployer.logs(deploy_ref))


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

    live_deploy = _live_deploy(session, org_id=org_id, site_id=current_site.id)
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
    _assert_exact_build_artifact(artifact=target_artifact, client_id=client_id, version=target_version)

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

    rollback_ref = target_version.build_hash
    if deployer.name == "vercel":
        target_deploy = session.scalar(select(Deploy).where(
            Deploy.org_id == org_id,
            Deploy.site_version_id == target_version.id,
            Deploy.provider == deployer.name,
            Deploy.url.is_not(None),
        ).order_by(Deploy.created_at.desc()))
        if target_deploy is None:
            raise DeployError("target Vercel deployment reference not found")
        rollback_ref = target_version.build_hash
    promoted = _as_deploy_error(
        "rollback", lambda: deployer.rollback(str(current_site.id), rollback_ref)
    )
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
    record_audit(
        session,
        org_id=org_id,
        actor="system",
        action="deployment.rolled_back",
        entity_type="deploy",
        entity_id=str(record.id),
        after={"client_id": str(client_id), "build_hash": target_version.build_hash, "url": record.url},
    )
    return record
