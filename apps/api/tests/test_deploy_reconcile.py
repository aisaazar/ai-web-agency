"""Crash-window recovery for the two-phase production promotion.

Publishing and rolling back promote the provider *before* the database records it, so a crash in
between used to leave the provider serving a build the database had never written down. These tests
fail at each boundary on purpose and assert what an operator would actually observe:

- the previous known-good deployment is never lost,
- a crash never yields a false "published" row,
- reconciliation converges to exactly one deterministic live deployment,
- running reconciliation again is harmless,
- an interrupted promotion whose approval was revoked fails instead of going live,
- an interrupted promotion from another organization is not reachable by one org's sweep.
"""

from __future__ import annotations

import pytest

from agency.db import create_all, create_session_factory
from agency.db.models import Approval, Artifact, BuildValidation, Client, Deploy, Org, Site, SiteVersion
from agency.db.workflow_models import PipelineRun
from agency.services import deploy_service as deploy_module
from agency.services.deployment_reconcile import reconcile_deployments
from agency.services.deploy_service import (
    PROMOTION_FAILED,
    PROMOTION_LIVE,
    PROMOTION_PENDING,
    PROMOTION_SUPERSEDED,
    DeployError,
    publish_site,
    rollback_site,
)

CHECKS = (
    "content_schema", "facts_provenance", "claims_policy", "required_legal_pages",
    "typecheck", "next_build", "linkcheck", "a11y_budget", "perf_budget",
    "playwright_smoke", "seo_manifest",
)


class CrashingPromoteProvider:
    """Promotes, then dies - the exact window that used to corrupt the deployment record."""

    name = "fake"

    def __init__(self, die_after_promote: bool = True, error: Exception | None = None):
        self.calls: list[str] = []
        self.die_after_promote = die_after_promote
        self.error = error

    def promote(self, deploy_ref):
        self.calls.append(deploy_ref)
        if self.error is not None:
            raise self.error
        if self.die_after_promote:
            # The provider has already switched production. The process now dies before the
            # database records it.
            raise SystemExit("simulated process crash after provider promotion")
        return type("Result", (), {
            "provider": self.name, "deploy_ref": deploy_ref, "status": "live",
            "url": f"https://preview.example/{deploy_ref}",
        })()

    def rollback(self, site_id, to_build_hash):
        self.calls.append(to_build_hash)
        if self.die_after_promote:
            raise SystemExit("simulated process crash after provider rollback")
        return type("Result", (), {
            "provider": self.name, "deploy_ref": to_build_hash, "status": "live",
            "url": f"https://preview.example/{to_build_hash}",
        })()


class RecordingProvider:
    """A well-behaved provider: promotion succeeds and is recorded."""

    name = "fake"

    def __init__(self):
        self.calls: list[str] = []

    def promote(self, deploy_ref):
        self.calls.append(deploy_ref)
        return type("Result", (), {
            "provider": self.name, "deploy_ref": deploy_ref, "status": "live",
            "url": f"https://preview.example/{deploy_ref}",
        })()

    def rollback(self, site_id, to_build_hash):
        self.calls.append(to_build_hash)
        return type("Result", (), {
            "provider": self.name, "deploy_ref": to_build_hash, "status": "live",
            "url": f"https://preview.example/{to_build_hash}",
        })()


def _seed(tmp_path, *, state="PREVIEW_APPROVED", slug="agency"):
    """A client that is fully approved and previewed, ready to publish."""
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    create_all(database_url)
    session = create_session_factory(database_url)()
    org = Org(name="Agency", slug=slug)
    session.add(org)
    session.flush()
    client = Client(org_id=org.id, name="Dental", slug="dental", category="dental")
    session.add(client)
    session.flush()
    site = Site(org_id=org.id, client_id=client.id, template_id="_template-base", design_preset_id="health")
    session.add(site)
    session.flush()
    content = Artifact(
        org_id=org.id, artifact_type="content_model", schema_version="1.0.0",
        payload_json={"client_id": str(client.id)},
    )
    session.add(content)
    session.flush()
    version = SiteVersion(
        org_id=org.id, site_id=site.id, build_hash="1" * 64, content_artifact_id=content.id,
        content_schema_version="1.0.0", template_version="1.0.0", design_preset_id="health",
    )
    session.add(version)
    session.flush()
    build_artifact = Artifact(
        org_id=org.id, artifact_type="site_build", schema_version="1.0.0",
        payload_json={"client_id": str(client.id), "site_version_id": str(version.id), "build_hash": version.build_hash},
        build_hash=version.build_hash, input_artifact_id=content.id, is_active=True,
    )
    session.add(build_artifact)
    session.flush()
    session.add(Approval(
        org_id=org.id, artifact_id=build_artifact.id, gate="PUBLISH",
        decision="approved", approved_by="owner@example.com",
    ))
    session.add(Deploy(
        org_id=org.id, site_version_id=version.id, environment="preview",
        provider="fake", status="preview_ready", url="https://preview.example/x",
    ))
    session.add_all([
        BuildValidation(org_id=org.id, site_version_id=version.id, check_name=name, passed=True, detail_json={})
        for name in CHECKS
    ])
    site.current_build_hash = version.build_hash
    session.add(PipelineRun(org_id=org.id, client_id=client.id, state=state))
    session.commit()
    return database_url, session, org, client, site, version


def _fresh(database_url):
    return create_session_factory(database_url)()


def _production_rows(session, org_id):
    return list(session.query(Deploy).filter(
        Deploy.org_id == org_id, Deploy.environment == "production",
    ).all())


def _live_rows(session, org_id):
    return [row for row in _production_rows(session, org_id) if row.status == PROMOTION_LIVE]

def test_crash_after_provider_promotion_leaves_a_reconcilable_pending_row(tmp_path):
    """Window 1: the provider promoted production, then the process died before the DB write."""
    database_url, session, org, client, site, version = _seed(tmp_path)
    provider = CrashingPromoteProvider(die_after_promote=True)

    with pytest.raises(SystemExit):
        publish_site(
            session, org_id=org.id, client_id=client.id,
            site_version_id=version.id, provider=provider,
        )

    # The intent is durable, and nothing claims to be live.
    reader = _fresh(database_url)
    rows = _production_rows(reader, org.id)
    assert [row.status for row in rows] == [PROMOTION_PENDING]
    assert rows[0].url is None, "an unconfirmed promotion must not carry a URL"
    reader.close()

    # Reconciliation converges it to exactly one live deployment.
    reader = _fresh(database_url)
    report = reconcile_deployments(reader, org_id=org.id, provider=RecordingProvider())
    assert report.promoted == [str(rows[0].id)]
    assert report.failed == []
    assert len(_live_rows(reader, org.id)) == 1
    reader.close()
    session.close()


def test_crash_leaves_the_previous_live_deployment_intact_until_reconciled(tmp_path):
    """A client already live on an older build must keep serving it across a crashed publish."""
    database_url, session, org, client, site, version = _seed(tmp_path)
    older = Deploy(
        org_id=org.id, site_version_id=version.id, environment="production",
        provider="fake", status=PROMOTION_LIVE, url="https://live.example/old",
    )
    session.add(older)
    session.commit()

    provider = CrashingPromoteProvider(die_after_promote=True)
    with pytest.raises(SystemExit):
        publish_site(
            session, org_id=org.id, client_id=client.id,
            site_version_id=version.id, provider=provider,
        )

    reader = _fresh(database_url)
    live = _live_rows(reader, org.id)
    assert [row.url for row in live] == ["https://live.example/old"], (
        "the last known-good deployment must still be the live one after a crash"
    )
    reader.close()

    # Only after reconciliation succeeds does the new build replace it.
    reader = _fresh(database_url)
    reconcile_deployments(reader, org_id=org.id, provider=RecordingProvider())
    live = _live_rows(reader, org.id)
    assert len(live) == 1
    assert live[0].url.endswith(version.build_hash)
    reader.close()
    session.close()


def test_provider_failure_never_creates_a_live_row(tmp_path):
    """Window 2: the provider refuses the promotion; nothing may claim to be live."""
    database_url, session, org, client, site, version = _seed(tmp_path)
    provider = CrashingPromoteProvider(error=DeployError("provider rejected the promotion"))

    with pytest.raises(DeployError, match="provider rejected"):
        publish_site(
            session, org_id=org.id, client_id=client.id,
            site_version_id=version.id, provider=provider,
        )

    reader = _fresh(database_url)
    rows = _production_rows(reader, org.id)
    assert [row.status for row in rows] == [PROMOTION_FAILED]
    assert _live_rows(reader, org.id) == []
    reader.close()

    # A failed promotion is terminal: reconciliation does not resurrect it.
    reader = _fresh(database_url)
    report = reconcile_deployments(reader, org_id=org.id, provider=RecordingProvider())
    assert report.changed == 0
    assert [row.status for row in _production_rows(reader, org.id)] == [PROMOTION_FAILED]
    reader.close()
    session.close()


def test_invalid_pipeline_state_is_rejected_before_the_provider_is_touched(tmp_path):
    """Window 3: a state that cannot publish must not reach the provider or the database."""
    database_url, session, org, client, site, version = _seed(tmp_path, state="DESIGN_APPROVED")
    provider = RecordingProvider()

    with pytest.raises(DeployError, match="not ready to publish"):
        publish_site(
            session, org_id=org.id, client_id=client.id,
            site_version_id=version.id, provider=provider,
        )

    assert provider.calls == [], "an invalid state must be rejected before any external side effect"
    reader = _fresh(database_url)
    assert _production_rows(reader, org.id) == [], "no promotion row may exist for a rejected publish"
    reader.close()
    session.close()


def test_transition_check_runs_before_the_provider_is_promoted(tmp_path, monkeypatch):
    """The transition check used to sit *after* the promotion, orphaning the provider.

    The state guard above normally catches this first, so the ordering is proven directly: with the
    transition itself invalidated, publish must refuse without ever calling the provider.
    """
    database_url, session, org, client, site, version = _seed(tmp_path)
    provider = RecordingProvider()
    monkeypatch.setattr(deploy_module, "is_valid_transition", lambda *_args: False)

    with pytest.raises(DeployError, match="cannot publish from state"):
        publish_site(
            session, org_id=org.id, client_id=client.id,
            site_version_id=version.id, provider=provider,
        )

    assert provider.calls == [], "the transition check must precede the external side effect"
    reader = _fresh(database_url)
    assert _production_rows(reader, org.id) == []
    reader.close()
    session.close()


def test_reconciliation_is_idempotent(tmp_path):
    database_url, session, org, client, site, version = _seed(tmp_path)
    with pytest.raises(SystemExit):
        publish_site(
            session, org_id=org.id, client_id=client.id,
            site_version_id=version.id, provider=CrashingPromoteProvider(),
        )

    reader = _fresh(database_url)
    first = reconcile_deployments(reader, org_id=org.id, provider=RecordingProvider())
    second = reconcile_deployments(reader, org_id=org.id, provider=RecordingProvider())
    third = reconcile_deployments(reader, org_id=org.id, provider=RecordingProvider())
    assert first.changed == 1
    assert second.changed == 0, "a second pass must be a no-op"
    assert third.changed == 0
    assert len(_live_rows(reader, org.id)) == 1
    reader.close()
    session.close()


def test_reconciliation_ignores_settled_deployments(tmp_path):
    """Only pending promotions are in scope; live/superseded/failed rows are never touched."""
    database_url, session, org, client, site, version = _seed(tmp_path)
    session.add(Deploy(org_id=org.id, site_version_id=version.id, environment="production",
                       provider="fake", status=PROMOTION_LIVE, url="https://live.example/a"))
    session.add(Deploy(org_id=org.id, site_version_id=version.id, environment="production",
                       provider="fake", status=PROMOTION_SUPERSEDED, url="https://live.example/b"))
    session.add(Deploy(org_id=org.id, site_version_id=version.id, environment="production",
                       provider="fake", status=PROMOTION_FAILED, url=None))
    session.commit()

    reader = _fresh(database_url)
    provider = RecordingProvider()
    report = reconcile_deployments(reader, org_id=org.id, provider=provider)
    assert report.changed == 0
    assert provider.calls == [], "settled deployments must not be re-promoted"
    reader.close()
    session.close()


def test_reconciliation_fails_a_promotion_whose_approval_was_revoked(tmp_path):
    """A pending row must never be promoted if its PUBLISH approval disappeared after the crash."""
    database_url, session, org, client, site, version = _seed(tmp_path)
    with pytest.raises(SystemExit):
        publish_site(
            session, org_id=org.id, client_id=client.id,
            site_version_id=version.id, provider=CrashingPromoteProvider(),
        )
    session.query(Approval).filter(Approval.org_id == org.id, Approval.gate == "PUBLISH").delete()
    session.commit()

    reader = _fresh(database_url)
    provider = RecordingProvider()
    report = reconcile_deployments(reader, org_id=org.id, provider=provider)
    assert report.promoted == []
    assert len(report.failed) == 1
    assert "publish approval" in report.failed[0][1]
    assert provider.calls == [], "an unapproved build must never be promoted during recovery"
    assert _live_rows(reader, org.id) == []
    reader.close()
    session.close()


def test_reconciliation_fails_a_promotion_whose_validations_disappeared(tmp_path):
    database_url, session, org, client, site, version = _seed(tmp_path)
    with pytest.raises(SystemExit):
        publish_site(
            session, org_id=org.id, client_id=client.id,
            site_version_id=version.id, provider=CrashingPromoteProvider(),
        )
    session.query(BuildValidation).filter(
        BuildValidation.org_id == org.id, BuildValidation.check_name == "playwright_smoke"
    ).delete()
    session.commit()

    reader = _fresh(database_url)
    provider = RecordingProvider()
    report = reconcile_deployments(reader, org_id=org.id, provider=provider)
    assert report.promoted == []
    assert "missing=playwright_smoke" in report.failed[0][1]
    assert provider.calls == []
    reader.close()
    session.close()


def test_reconciliation_is_org_scoped(tmp_path):
    """One organization's sweep must never converge another organization's pending row."""
    database_url, session, org, client, site, version = _seed(tmp_path)
    with pytest.raises(SystemExit):
        publish_site(
            session, org_id=org.id, client_id=client.id,
            site_version_id=version.id, provider=CrashingPromoteProvider(),
        )

    other = Org(name="Other", slug="other")
    session.add(other)
    session.commit()

    reader = _fresh(database_url)
    provider = RecordingProvider()
    report = reconcile_deployments(reader, org_id=other.id, provider=provider)
    assert report.changed == 0
    assert [row.status for row in _production_rows(reader, org.id)] == [PROMOTION_PENDING]
    reader.close()
    session.close()


def test_crash_during_rollback_is_reconcilable(tmp_path):
    """Rollback has the same window and the same recovery path."""
    database_url, session, org, client, site, version = _seed(tmp_path, state="LIVE")
    session.add(Deploy(org_id=org.id, site_version_id=version.id, environment="production",
                       provider="fake", status=PROMOTION_LIVE, url="https://live.example/current"))
    session.commit()

    with pytest.raises(SystemExit):
        rollback_site(
            session, org_id=org.id, client_id=client.id,
            build_hash=version.build_hash, provider=CrashingPromoteProvider(),
        )

    reader = _fresh(database_url)
    assert [row.status for row in _production_rows(reader, org.id)] == [
        PROMOTION_LIVE, PROMOTION_PENDING,
    ]
    report = reconcile_deployments(reader, org_id=org.id, provider=RecordingProvider())
    assert len(report.promoted) == 1
    assert len(_live_rows(reader, org.id)) == 1
    reader.close()
    session.close()


def test_successful_publish_leaves_exactly_one_live_deployment(tmp_path):
    database_url, session, org, client, site, version = _seed(tmp_path)
    record = publish_site(
        session, org_id=org.id, client_id=client.id,
        site_version_id=version.id, provider=RecordingProvider(),
    )
    assert record.status == PROMOTION_LIVE

    reader = _fresh(database_url)
    assert len(_live_rows(reader, org.id)) == 1
    assert _production_rows(reader, org.id)[0].url.endswith(version.build_hash)
    reader.close()
    session.close()


def test_publish_then_rollback_keeps_one_live_and_supersedes_the_rest(tmp_path):
    database_url, session, org, client, site, version = _seed(tmp_path, state="PREVIEW_APPROVED")
    publish_site(session, org_id=org.id, client_id=client.id,
                 site_version_id=version.id, provider=RecordingProvider())
    rollback_site(session, org_id=org.id, client_id=client.id,
                  build_hash=version.build_hash, provider=RecordingProvider())

    reader = _fresh(database_url)
    rows = _production_rows(reader, org.id)
    assert len(_live_rows(reader, org.id)) == 1
    assert all(row.status in {PROMOTION_LIVE, PROMOTION_SUPERSEDED} for row in rows)
    reader.close()
    session.close()
