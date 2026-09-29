import pytest
from sqlalchemy import select

from agency.db import create_all, create_session_factory
from agency.db.models import Approval, Artifact, BuildValidation, Client, Deploy, Org, Site, SiteVersion
from agency.db.workflow_models import PipelineRun
from agency.services.deploy_service import DeployError, attach_domain, create_preview, deployment_logs, rollback_site


CHECKS = (
    "content_schema", "facts_provenance", "claims_policy", "required_legal_pages",
    "typecheck", "next_build", "linkcheck", "a11y_budget", "perf_budget",
    "playwright_smoke", "seo_manifest",
)


class FakeDeploymentProvider:
    name = "fake"

    def __init__(self):
        self.calls = []

    def rollback(self, site_id, to_build_hash):
        self.calls.append((site_id, to_build_hash))
        return type("Result", (), {
            "provider": self.name, "deploy_ref": to_build_hash,
            "status": "live", "url": f"https://preview.example/{to_build_hash}",
        })()

    def attach_domain(self, site_id, fqdn):
        self.calls.append(("domain", site_id, fqdn))
        return type("Result", (), {"provider": self.name, "fqdn": fqdn, "status": "attached"})()

    def logs(self, deploy_ref):
        self.calls.append(("logs", deploy_ref))
        return f"logs:{deploy_ref}"


def _seed(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    create_all(database_url)
    session = create_session_factory(database_url)()
    org = Org(name="Agency", slug="agency")
    session.add(org)
    session.flush()
    client = Client(org_id=org.id, name="Dental", slug="dental", category="dental")
    session.add(client)
    session.flush()
    site = Site(org_id=org.id, client_id=client.id, template_id="_template-base", design_preset_id="health")
    session.add(site)
    session.flush()

    current_content = Artifact(org_id=org.id, artifact_type="content_model", schema_version="1.0.0", payload_json={"client_id": str(client.id)})
    target_content = Artifact(org_id=org.id, artifact_type="content_model", schema_version="1.0.0", payload_json={"client_id": str(client.id)})
    session.add_all([current_content, target_content])
    session.flush()
    current = SiteVersion(org_id=org.id, site_id=site.id, build_hash="1" * 64, content_artifact_id=current_content.id,
                          content_schema_version="1.0.0", template_version="1.0.0", design_preset_id="health")
    target = SiteVersion(org_id=org.id, site_id=site.id, build_hash="2" * 64, content_artifact_id=target_content.id,
                         content_schema_version="1.0.0", template_version="1.0.0", design_preset_id="health")
    session.add_all([current, target])
    session.flush()
    target_artifact = Artifact(org_id=org.id, artifact_type="site_build", schema_version="1.0.0",
                               payload_json={"client_id": str(client.id), "site_version_id": str(target.id), "build_hash": target.build_hash},
                               build_hash=target.build_hash, input_artifact_id=target_content.id)
    session.add(target_artifact)
    session.flush()
    session.add(Approval(org_id=org.id, artifact_id=target_artifact.id, gate="PUBLISH", decision="approved",
                         approved_by="owner@example.com"))
    session.add_all([BuildValidation(org_id=org.id, site_version_id=target.id, check_name=name, passed=True, detail_json={})
                     for name in CHECKS])
    session.add(Deploy(org_id=org.id, site_version_id=current.id, environment="production",
                       provider="fake", status="live", url="https://live.example"))
    session.commit()
    return session, org, client, site, target


def test_rollback_promotes_exact_approved_build(tmp_path):
    session, org, client, site, target = _seed(tmp_path)
    provider = FakeDeploymentProvider()

    record = rollback_site(
        session, org_id=org.id, client_id=client.id,
        build_hash=target.build_hash, provider=provider,
    )

    assert provider.calls == [(str(site.id), target.build_hash)]
    assert record.status == "live"
    assert record.site_version_id == target.id
    assert site.current_build_hash == target.build_hash
    assert record.url.endswith(target.build_hash)
    session.close()


def test_rollback_rejects_unknown_build_hash(tmp_path):
    session, org, client, _, _ = _seed(tmp_path)
    with pytest.raises(DeployError, match="not a site version"):
        rollback_site(session, org_id=org.id, client_id=client.id, build_hash="3" * 64)
    session.close()


def test_rollback_rejects_inconsistent_artifact_site_version_binding(tmp_path):
    session, org, client, site, target = _seed(tmp_path)
    artifact = session.scalar(select(Artifact).where(
        Artifact.org_id == org.id,
        Artifact.artifact_type == "site_build",
        Artifact.build_hash == target.build_hash,
    ))
    artifact.payload_json = {**artifact.payload_json, "site_version_id": str(site.id)}
    session.flush()
    provider = FakeDeploymentProvider()

    with pytest.raises(DeployError, match="site_version binding is inconsistent"):
        rollback_site(
            session,
            org_id=org.id,
            client_id=client.id,
            build_hash=target.build_hash,
            provider=provider,
        )

    assert provider.calls == []
    session.close()


def test_rollback_rejects_inconsistent_artifact_client_binding(tmp_path):
    session, org, client, _, target = _seed(tmp_path)
    artifact = session.scalar(select(Artifact).where(
        Artifact.org_id == org.id,
        Artifact.artifact_type == "site_build",
        Artifact.build_hash == target.build_hash,
    ))
    artifact.payload_json = {
        **artifact.payload_json,
        "client_id": "00000000-0000-0000-0000-000000000000",
    }
    session.flush()
    provider = FakeDeploymentProvider()

    with pytest.raises(DeployError, match="client binding is inconsistent"):
        rollback_site(
            session,
            org_id=org.id,
            client_id=client.id,
            build_hash=target.build_hash,
            provider=provider,
        )

    assert provider.calls == []
    session.close()

def test_create_preview_rejects_existing_preview_from_different_provider(tmp_path):
    session, org, client, site, target = _seed(tmp_path)
    session.add(PipelineRun(org_id=org.id, client_id=client.id, state="PREVIEW_READY"))
    session.add(Deploy(
        org_id=org.id,
        site_version_id=target.id,
        environment="preview",
        provider="local_static",
        status="preview_ready",
        url="file:///preview/target",
    ))
    session.commit()

    class AlternateProvider:
        name = "vercel"

        def __init__(self):
            self.calls = 0

        def create_preview(self, bundle):
            self.calls += 1
            raise AssertionError("provider must not be called when preview provider mismatches")

    provider = AlternateProvider()
    with pytest.raises(DeployError, match="does not match requested provider"):
        create_preview(
            session,
            org_id=org.id,
            client_id=client.id,
            site_version_id=target.id,
            provider=provider,
        )

    assert provider.calls == 0
    session.close()


def test_attach_domain_requires_live_site_and_normalizes_fqdn(tmp_path):
    session, org, client, site, _ = _seed(tmp_path)
    provider = FakeDeploymentProvider()
    result = attach_domain(session, org_id=org.id, client_id=client.id,
                           fqdn="Clinic.Example.DE.", provider=provider)
    assert result.fqdn == "clinic.example.de"
    assert provider.calls[-1] == ("domain", str(site.id), "clinic.example.de")
    session.close()


def test_attach_domain_rejects_path_or_scheme(tmp_path):
    session, org, client, _, _ = _seed(tmp_path)
    with pytest.raises(DeployError, match="valid DNS hostname"):
        attach_domain(session, org_id=org.id, client_id=client.id,
                      fqdn="https://clinic.example.de/path", provider=FakeDeploymentProvider())
    session.close()


def test_deployment_logs_are_scoped_to_client(tmp_path):
    session, org, client, _, _ = _seed(tmp_path)
    deploy = session.scalar(select(Deploy).where(Deploy.org_id == org.id))
    provider = FakeDeploymentProvider()
    result = deployment_logs(session, org_id=org.id, client_id=client.id,
                              deploy_id=deploy.id, provider=provider)
    assert result.startswith("logs:")
    session.close()


def test_deployment_logs_reject_cross_client(tmp_path):
    session, org, client, _, _ = _seed(tmp_path)
    other = Client(org_id=org.id, name="Other", slug="other", category="dental")
    session.add(other)
    session.flush()
    deploy = session.scalar(select(Deploy).where(Deploy.org_id == org.id))
    with pytest.raises(DeployError, match="does not belong to this client"):
        deployment_logs(session, org_id=org.id, client_id=other.id,
                        deploy_id=deploy.id, provider=FakeDeploymentProvider())
    session.close()
