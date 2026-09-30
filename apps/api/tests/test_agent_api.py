import anyio
import httpx

import agency.api.agent as agent_api
from agency.api import create_app
from agency.db.conversation_models import ConversationMessage
from agency.db.models import Approval, Artifact, Client, Org
from agency.db.session import create_all, create_session_factory
from agency.services.agent_service import CONSENT_NOTICE


def _seed(database_url):
    create_all(database_url)
    session = create_session_factory(database_url)()
    org = Org(name="Agency", slug="agency")
    session.add(org)
    session.flush()
    client = Client(org_id=org.id, name="Praxis", slug="praxis", category="dental")
    session.add(client)
    session.flush()
    facts_artifact = Artifact(
        org_id=org.id,
        artifact_type="business_facts",
        schema_version="1.0.0",
        payload_json={"client_id": str(client.id), "facts": []},
        revision=1,
        is_active=True,
    )
    session.add(facts_artifact)
    session.flush()
    artifact = Artifact(
        org_id=org.id,
        artifact_type="content_model",
        schema_version="1.0.0",
        payload_json={
            "content_schema_version": "1.0.0",
            "faq": {
                "items": [
                    {
                        "question": "Wie vereinbare ich einen Termin?",
                        "answer": ["Über das Anfrageformular oder telefonisch."]
                    }
                ]
            },
            "business": {
                "contact": {
                    "phone": "+49 911 555 0198",
                    "email": "hallo@example.test",
                }
            },
        },
        revision=1,
        input_artifact_id=facts_artifact.id,
        is_active=True,
    )
    session.add(artifact)
    session.flush()
    session.add(
        Approval(
            org_id=org.id,
            artifact_id=artifact.id,
            gate="CONTENT",
            decision="approved",
            approved_by="reviewer@example.test",
        )
    )
    session.commit()
    session.close()
    return org, client


def _request(app, method, path, **kwargs):
    async def request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, **kwargs)

    return anyio.run(request)


def test_agent_requires_consent_and_answers_from_approved_content(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agent.db'}"
    _, client = _seed(database_url)
    app = create_app(database_url)

    blocked = _request(
        app,
        "POST",
        f"/v1/agent/clients/{client.id}/conversations",
        json={"consent": False},
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == CONSENT_NOTICE

    async def flow():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            started = await http.post(
                f"/v1/agent/clients/{client.id}/conversations",
                json={"consent": True},
            )
            conversation_id = started.json()["conversation_id"]
            visitor_token = started.json()["visitor_token"]
            http.cookies.clear()
            answered = await http.post(
                f"/v1/agent/conversations/{conversation_id}/messages",
                headers={"X-Agent-Visitor-Token": visitor_token},
                json={"message": "Wie vereinbare ich einen Termin?"},
            )
            history = await http.get(
                f"/v1/agent/conversations/{conversation_id}/messages",
                headers={"X-Agent-Visitor-Token": visitor_token},
            )
            return started, answered, history

    started, answered, history = anyio.run(flow)
    assert started.status_code == 201
    assert "HttpOnly" in started.headers["set-cookie"]
    assert answered.status_code == 200
    assert "Anfrageformular" in answered.json()["message"]
    assert answered.json()["escalated"] is False
    assert history.status_code == 200
    assert len(history.json()) == 2


def test_agent_refuses_medical_advice_and_escalates(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agent.db'}"
    _, client = _seed(database_url)
    app = create_app(database_url)

    async def flow():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            started = await http.post(
                f"/v1/agent/clients/{client.id}/conversations",
                json={"consent": True},
            )
            return await http.post(
                f"/v1/agent/conversations/{started.json()['conversation_id']}/messages",
                json={"message": "Welche Medikamente und Dosierung brauche ich?"},
            )

    response = anyio.run(flow)
    assert response.status_code == 200
    assert response.json()["escalated"] is True
    assert "individuelle medizinische" in response.json()["message"]


def test_agent_redacts_pii_in_transcript(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'agent.db'}"
    _, client = _seed(database_url)
    app = create_app(database_url)

    async def flow():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            started = await http.post(
                f"/v1/agent/clients/{client.id}/conversations",
                json={"consent": True},
            )
            conversation_id = started.json()["conversation_id"]
            response = await http.post(
                f"/v1/agent/conversations/{conversation_id}/messages",
                json={"message": "Termin für jane@example.com oder +49 911 123456"},
            )
            history = await http.get(
                f"/v1/agent/conversations/{conversation_id}/messages"
            )
            return response, history

    response, history = anyio.run(flow)
    assert response.status_code == 200
    assert history.status_code == 200
    user_message = history.json()[0]["message"]
    assert "jane@example.com" not in user_message
    assert "+49 911 123456" not in user_message
    assert "[E-MAIL REDACTED]" in user_message
    assert "[PHONE REDACTED]" in user_message


def test_agent_rate_limits_conversation_starts_and_messages(tmp_path, monkeypatch):
    from agency.services import rate_limit_service

    rate_limit_service.reset()
    monkeypatch.setattr(agent_api, "_START_LIMIT", 1)
    monkeypatch.setattr(agent_api, "_START_WINDOW_SECONDS", 60)
    database_url = f"sqlite:///{tmp_path / 'agent-rate.db'}"
    _, client = _seed(database_url)
    app = create_app(database_url)

    first = _request(
        app,
        "POST",
        f"/v1/agent/clients/{client.id}/conversations",
        json={"consent": True},
    )
    blocked_start = _request(
        app,
        "POST",
        f"/v1/agent/clients/{client.id}/conversations",
        json={"consent": True},
    )
    assert first.status_code == 201
    assert blocked_start.status_code == 429
    assert blocked_start.headers["retry-after"] == "60"

    rate_limit_service.reset()
    monkeypatch.setattr(agent_api, "_MESSAGE_LIMIT", 1)
    monkeypatch.setattr(agent_api, "_MESSAGE_WINDOW_SECONDS", 60)
    conversation_id = first.json()["conversation_id"]
    visitor_token = first.json()["visitor_token"]
    allowed = _request(
        app,
        "POST",
        f"/v1/agent/conversations/{conversation_id}/messages",
        headers={"X-Agent-Visitor-Token": visitor_token},
        json={"message": "Wie vereinbare ich einen Termin?"},
    )
    blocked_message = _request(
        app,
        "POST",
        f"/v1/agent/conversations/{conversation_id}/messages",
        headers={"X-Agent-Visitor-Token": visitor_token},
        json={"message": "Wie vereinbare ich einen Termin?"},
    )
    assert allowed.status_code == 200
    assert blocked_message.status_code == 429
    assert blocked_message.headers["retry-after"] == "60"
    rate_limit_service.reset()
