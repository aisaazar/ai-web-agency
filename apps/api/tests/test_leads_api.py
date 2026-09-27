import anyio
import httpx

from agency.api import create_app
from agency.db.models import Client, Org, Site
from agency.db.session import create_all, create_session_factory


def _seed(database_url):
    create_all(database_url)
    factory = create_session_factory(database_url)
    session = factory()
    org = Org(name="Agency", slug="agency")
    session.add(org)
    session.flush()
    client = Client(org_id=org.id, name="Dental", slug="dental", category="dental")
    session.add(client)
    session.flush()
    site = Site(org_id=org.id, client_id=client.id, template_id="base", design_preset_id="health")
    session.add(site)
    session.commit()
    session.close()
    return site


def _post(app, payload):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post("/v1/leads", json=payload)
    return anyio.run(request)


def test_lead_api_persists_a_real_lead(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    site = _seed(database_url)
    response = _post(create_app(database_url), {
        "site_id": str(site.id),
        "name": "Jane Doe",
        "email": "jane@example.com",
        "phone": "+49 911 123456",
        "message": "Ich möchte einen Termin vereinbaren.",
        "consent": True,
    })
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "new"


def test_lead_api_rejects_missing_consent(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    site = _seed(database_url)
    response = _post(create_app(database_url), {
        "site_id": str(site.id), "name": "Jane", "email": "jane@example.com",
        "message": "Hello", "consent": False,
    })
    assert response.status_code == 400


def _request(app, method, path, **kwargs):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)
    return anyio.run(request)


def test_lead_status_history_is_persisted(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    site = _seed(database_url)
    app = create_app(database_url)
    created = _post(app, {
        "site_id": str(site.id),
        "name": "Jane Doe",
        "email": "jane@example.com",
        "message": "Please call me.",
        "consent": True,
    })
    lead_id = created.json()["id"]

    changed = _request(
        app,
        "PATCH",
        f"/v1/leads/{lead_id}/status?org_id={site.org_id}",
        json={"status": "contacted", "actor": "owner", "note": "Called client"},
    )
    assert changed.status_code == 200
    assert changed.json()["status"] == "contacted"

    events = _request(
        app,
        "GET",
        f"/v1/leads/{lead_id}/events?org_id={site.org_id}",
    )
    assert events.status_code == 200
    payload = events.json()
    assert len(payload) == 2
    assert payload[0]["to_status"] == "new"
    assert payload[1]["from_status"] == "new"
    assert payload[1]["to_status"] == "contacted"


def test_lead_status_is_org_scoped(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    site = _seed(database_url)
    app = create_app(database_url)
    created = _post(app, {
        "site_id": str(site.id),
        "name": "Jane Doe",
        "email": "jane@example.com",
        "message": "Please call me.",
        "consent": True,
    })
    lead_id = created.json()["id"]

    from agency.db.models import Org
    session = create_session_factory(database_url)()
    other_org = Org(name="Other", slug="other")
    session.add(other_org)
    session.commit()
    session.close()

    response = _request(
        app,
        "GET",
        f"/v1/leads/{lead_id}/events?org_id={other_org.id}",
    )
    assert response.status_code == 404



def test_new_lead_notification_runs_after_commit(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    site = _seed(database_url)
    app = create_app(database_url)

    class FakeNotifyProvider:
        name = "fake"
        def __init__(self):
            self.messages = []
        def send(self, notification):
            self.messages.append(notification)

    provider = FakeNotifyProvider()
    import agency.services.lead_service as lead_service
    monkeypatch.setattr(lead_service, "get_notify_provider", lambda: provider)

    response = _post(app, {
        "site_id": str(site.id),
        "name": "Jane Doe",
        "email": "jane@example.com",
        "message": "Please call me.",
        "consent": True,
    })

    assert response.status_code == 201
    assert len(provider.messages) == 1
    assert "Jane Doe" in provider.messages[0].body



def test_lead_list_and_csv_export_are_org_scoped(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agency.db'}"
    site = _seed(database_url)
    app = create_app(database_url)
    created = _post(app, {
        "site_id": str(site.id),
        "name": "Jane Doe",
        "email": "jane@example.com",
        "message": "Please call me.",
        "consent": True,
    })
    assert created.status_code == 201

    listed = _request(app, "GET", f"/v1/leads?org_id={site.org_id}")
    assert listed.status_code == 200
    assert listed.json()[0]["email"] == "jane@example.com"

    exported = _request(app, "GET", f"/v1/leads/export.csv?org_id={site.org_id}")
    assert exported.status_code == 200
    assert "text/csv" in exported.headers["content-type"]
    assert "Jane Doe" in exported.text
    assert "Content-Disposition" in exported.headers

    from agency.db.models import Org
    session = create_session_factory(database_url)()
    other_org = Org(name="Other", slug="other")
    session.add(other_org)
    session.commit()
    session.close()

    other_list = _request(app, "GET", f"/v1/leads?org_id={other_org.id}")
    assert other_list.status_code == 200
    assert other_list.json() == []
