"""Reconcile production deployments that were interrupted mid-promotion.

Publishing and rolling back are two-phase. The intent is committed as a durable ``promoting`` row
*before* the provider is asked to move production, and the row only becomes ``live`` once the
provider confirmed. A crash between those two points is the one failure mode a database transaction
cannot protect against, because the provider change is external and survives the rollback of the
database write. It leaves exactly one observable trace: a ``promoting`` row.

This module converges those rows. It is deliberately a state machine rather than a try/except
cleanup, because the crash already happened by the time anything runs:

- deterministic: pending rows are processed oldest-first, so the same input always converges to the
  same single live deployment;
- idempotent and safe to repeat: only ``promoting`` rows are touched, so a second run is a no-op;
- authorization-preserving: the exact gates a publish must pass (org/client binding, immutable build
  artifact, PUBLISH approval, complete validation set) are re-checked before any promotion is
  re-driven. A pending row whose approval was revoked meanwhile is failed, never promoted;
- non-destructive: the previously live deployment is only superseded once a replacement is confirmed
  live, so the last known-good build stays recoverable throughout.

For a provider to be reconcilable at all, ``promote`` must be idempotent for a given reference. Both
shipped providers satisfy this: ``local_static.promote`` is a pure lookup of an immutable directory,
and ``VercelDeploymentProvider.promote`` re-points the production alias at the same deployment id.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Artifact, Deploy, Site, SiteVersion
from agency.providers.deploy import DeploymentProvider
from agency.providers.deployment_registry import get_deployment_provider
from agency.services.deploy_service import (
    PROMOTION_FAILED,
    PROMOTION_LIVE,
    RECONCILABLE_STATUSES,
    DeployError,
    _activate_live_deploy,
    _assert_exact_build_artifact,
    _assert_validations,
    _fail_promotion,
    _published_build_artifact,
)


class ReconcileReport:
    """Outcome of one reconciliation pass, suitable for logs and operator output."""

    def __init__(self) -> None:
        self.promoted: list[str] = []
        self.failed: list[tuple[str, str]] = []

    @property
    def changed(self) -> int:
        return len(self.promoted) + len(self.failed)

    def as_dict(self) -> dict:
        return {"promoted": list(self.promoted), "failed": [list(item) for item in self.failed]}


def _promote_reference(deploy: Deploy, version: SiteVersion, deployer: DeploymentProvider) -> str:
    """The reference to re-promote: an existing provider URL, or the immutable build hash."""
    if deployer.name == "vercel" and deploy.url:
        # A Vercel promotion targets the preview deployment's own reference, not the build hash.
        return deploy.url
    return version.build_hash
def _reconcile_one(
    session: Session,
    *,
    deploy: Deploy,
    provider: DeploymentProvider | None = None,
) -> tuple[str, str | None]:
    """Drive one pending promotion to a terminal state. Returns (outcome, reason)."""
    org_id = deploy.org_id
    version = session.scalar(select(SiteVersion).where(
        SiteVersion.id == deploy.site_version_id,
        SiteVersion.org_id == org_id,
    ))
    if version is None:
        _fail_promotion(session, deploy, "site version no longer exists")
        return PROMOTION_FAILED, "site version no longer exists"

    site = session.scalar(select(Site).where(
        Site.id == version.site_id,
        Site.org_id == org_id,
    ))
    if site is None:
        _fail_promotion(session, deploy, "site no longer exists")
        return PROMOTION_FAILED, "site no longer exists"

    # The owning client is derived from the site, never from the deploy row, so a pending row can
    # never be reconciled against a client it does not belong to.
    client_id = site.client_id

    # The exact invariants a publish must satisfy. A pending row that no longer qualifies - because
    # its build artifact was superseded or its approval was revoked - must never be promoted.
    try:
        _assert_validations(
            session,
            org_id=org_id,
            site_version_id=version.id,
            build_hash=version.build_hash,
        )
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
        _published_build_artifact(session, org_id=org_id, client_id=client_id, version=version)
    except DeployError as exc:
        reason = str(exc)
        _fail_promotion(session, deploy, reason)
        return PROMOTION_FAILED, reason

    deployer = provider or get_deployment_provider(deploy.provider)
    if deployer.name != deploy.provider:
        reason = f"deployment provider does not match stored deployment ({deployer.name})"
        _fail_promotion(session, deploy, reason)
        return PROMOTION_FAILED, reason

    try:
        promoted = deployer.promote(_promote_reference(deploy, version, deployer))
    except Exception as exc:
        reason = f"reconcile promotion failed: {exc}"
        _fail_promotion(session, deploy, reason)
        return PROMOTION_FAILED, reason

    _activate_live_deploy(
        session,
        org_id=org_id,
        site=site,
        record=deploy,
        url=promoted.url,
        build_hash=version.build_hash,
        audit_action="deployment.reconciled",
        audit_after={
            "client_id": str(client_id),
            "build_hash": version.build_hash,
            "url": promoted.url,
            "reconciled": True,
        },
    )
    return PROMOTION_LIVE, None


def reconcile_deployments(
    session: Session,
    *,
    org_id: UUID | None = None,
    provider: DeploymentProvider | None = None,
) -> ReconcileReport:
    """Converge every interrupted production promotion in scope.

    Scoped to a single organization unless `org_id` is omitted, in which case every organization is
    swept (the operator/CLI path). Safe to run repeatedly: it only writes rows still marked
    `promoting`, and each convergence is a single transaction, so a concurrent publish is unaffected.
    """
    report = ReconcileReport()
    query = select(Deploy).where(
        Deploy.environment == "production",
        Deploy.status.in_(RECONCILABLE_STATUSES),
    )
    if org_id is not None:
        query = query.where(Deploy.org_id == org_id)
    # Oldest first: if a site somehow has more than one pending promotion, the earliest is applied
    # and then superseded by the later one, which is the order the original requests arrived in.
    pending = list(session.scalars(query.order_by(Deploy.created_at.asc(), Deploy.id.asc())))

    for deploy in pending:
        outcome, reason = _reconcile_one(
            session,
            deploy=deploy,
            provider=provider if (provider is not None and provider.name == deploy.provider) else None,
        )
        if outcome == PROMOTION_LIVE:
            report.promoted.append(str(deploy.id))
        else:
            report.failed.append((str(deploy.id), reason or "unknown"))
    return report