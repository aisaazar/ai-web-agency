import anyio
import httpx

from agency.api import create_app
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
