import anyio
import httpx

from agency.api import create_app
from agency.api.dashboard import build_router as build_dashboard_router
from agency.db.models import Org
from agency.db.session import create_session_factory


def test_dashboard_returns_empty_real_api_shape_for_empty_org(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'dashboard.db'}"
    app = create_app(database_url)
    session = create_session_factory(database_url)()
    org = Org(name="Dashboard Agency", slug="dashboard-agency")
    session.add(org)
    session.commit()
    session.close()

    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(f"/v1/dashboard/overview?org_id={org.id}")

    response = anyio.run(request)

    assert response.status_code == 200
    assert response.json() == {
        "org_id": str(org.id),
        "counts": {
            "clients": 0,
            "artifacts": 0,
            "deployments": 0,
            "new_leads": 0,
        },
        "clients": [],
        "artifacts": [],
        "deployments": [],
        "leads": [],
    }

def test_dashboard_llm_cost_report_is_org_scoped(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'dashboard-cost.db'}"
    app = create_app(database_url)
    session = create_session_factory(database_url)()
    org = Org(name="Cost Agency", slug="cost-agency", llm_budget_micros=1000)
    session.add(org)
    session.flush()
    from agency.db.llm_budget_models import ClientLLMBudget
    from agency.db.models import Client, LLMInvocation

    client = Client(org_id=org.id, name="Dental", slug="dental", category="dental")
    session.add(client)
    session.flush()
    session.add(ClientLLMBudget(org_id=org.id, client_id=client.id, budget_micros=400))
    session.add(
        LLMInvocation(
            org_id=org.id,
            client_id=client.id,
            provider="test-paid",
            model="test-model",
            prompt_hash="a" * 64,
            tokens_in=10,
            tokens_out=20,
            cost_micros=123,
            latency_ms=10,
            status="completed",
        )
    )
    session.commit()
    session.close()

    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(f"/v1/dashboard/llm-cost?org_id={org.id}")

    response = anyio.run(request)
    assert response.status_code == 200
    assert response.json()["budget_micros"] == 1000
    assert response.json()["spent_micros"] == 123
    assert response.json()["clients"] == [
        {
            "client_id": str(client.id),
            "client_name": "Dental",
            "budget_micros": 400,
            "spent_micros": 123,
        }
    ]
def test_dashboard_client_detail_is_tenant_scoped_and_traces_artifacts(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'dashboard-detail.db'}"
    app = create_app(database_url)
    session = create_session_factory(database_url)()

    org = Org(name="Detail Agency", slug="detail-agency")
    other_org = Org(name="Other Agency", slug="other-agency")
    session.add_all([org, other_org])
    session.flush()

    from agency.db.models import Approval, Artifact, Client, Deploy, Site, SiteVersion
    from agency.db.workflow_models import PipelineRun

    client = Client(org_id=org.id, name="Dental", slug="dental", category="dental")
    other_client = Client(org_id=other_org.id, name="Other Dental", slug="other-dental", category="dental")
    session.add_all([client, other_client])
    session.flush()

    session.add(PipelineRun(org_id=org.id, client_id=client.id, state="CONTENT_COMPLETE"))
    from agency.db.models import ClientFact
    session.add(ClientFact(
        org_id=org.id,
        client_id=client.id,
        key="phone",
        value="+49 911 123456",
        value_type="text",
        source_kind="client",
        source_ref="intake:manual",
        confidence=1.0,
        status="proposed",
    ))
    facts = Artifact(
        org_id=org.id,
        artifact_type="business_facts",
        schema_version="1.0.0",
        payload_json={"client_id": str(client.id), "facts": []},
        revision=1,
        is_active=True,
    )
    session.add(facts)
    session.flush()

    content = Artifact(
        org_id=org.id,
        artifact_type="content_model",
        schema_version="1.0.0",
        payload_json={"content_schema_version": "1.0.0"},
        input_artifact_id=facts.id,
        revision=1,
        is_active=True,
    )
    unrelated = Artifact(
        org_id=other_org.id,
        artifact_type="business_facts",
        schema_version="1.0.0",
        payload_json={"client_id": str(other_client.id), "facts": []},
        revision=1,
        is_active=True,
    )
    session.add_all([content, unrelated])
    session.flush()

    session.add(Approval(
        org_id=org.id,
        artifact_id=content.id,
        gate="CONTENT",
        decision="approved",
        approved_by="reviewer",
    ))

    site = Site(
        org_id=org.id,
        client_id=client.id,
        template_id="_template-base",
        design_preset_id="health",
    )
    session.add(site)
    session.flush()
    version = SiteVersion(
        org_id=org.id,
        site_id=site.id,
        build_hash="a" * 64,
        content_artifact_id=content.id,
        content_schema_version="1.0.0",
        template_version="1.0.0",
        design_preset_id="health",
    )
    session.add(version)
    session.flush()
    session.add(Deploy(
        org_id=org.id,
        site_version_id=version.id,
        environment="preview",
        provider="local_static",
        status="preview",
        url="local://preview",
    ))
    session.commit()
    session.close()

    async def request(path):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    response = anyio.run(request, f"/v1/dashboard/clients/{client.id}?org_id={org.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["client"]["state"] == "CONTENT_COMPLETE"
    assert body["facts"] == [
        {
            "id": body["facts"][0]["id"],
            "key": "phone",
            "value": "+49 911 123456",
            "value_type": "text",
            "source_kind": "client",
            "source_ref": "intake:manual",
            "confidence": 1.0,
            "status": "proposed",
            "approved_by": None,
            "created_at": body["facts"][0]["created_at"],
        }
    ]
    assert {item["type"] for item in body["artifacts"]} == {"business_facts", "content_model"}
    assert body["approvals"][0]["gate"] == "CONTENT"
    assert body["site_versions"][0]["build_hash"] == "a" * 64
    assert body["deployments"][0]["status"] == "preview"

    blocked = anyio.run(request, f"/v1/dashboard/clients/{other_client.id}?org_id={org.id}")
    assert blocked.status_code == 404


def test_legacy_dashboard_collection_route_is_removed(tmp_path):
    """The untyped GET /v1/dashboard duplicate must not come back.

    It had no consumer, no response model, and an "infer the org" fallback that the typed
    /overview, /clients/{id} and /llm-cost routes deliberately do not have.
    """
    database_url = f"sqlite:///{tmp_path / 'dashboard-legacy.db'}"
    app = create_app(database_url)
    session = create_session_factory(database_url)()
    org = Org(name="Legacy Agency", slug="legacy-agency")
    session.add(org)
    session.commit()
    session.close()

    async def request(path):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    legacy = anyio.run(request, "/v1/dashboard")
    assert legacy.status_code == 404

    overview = anyio.run(request, f"/v1/dashboard/overview?org_id={org.id}")
    assert overview.status_code == 200
    assert overview.json()["org_id"] == str(org.id)

    dashboard_paths = {route.path for route in build_dashboard_router(None).routes}
    assert dashboard_paths == {
        "/v1/dashboard/overview",
        "/v1/dashboard/clients/{client_id}",
        "/v1/dashboard/llm-cost",
    }

