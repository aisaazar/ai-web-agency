from uuid import uuid4

from agency.db.base import Base
from agency.db.models import Client, ClientFact, Org
from agency.db.session import create_session_factory
from agency.repositories import ClientFactRepository


def _session():
    factory = create_session_factory("sqlite:///:memory:")
    Base.metadata.create_all(factory.kw["bind"])
    return factory()


def test_only_approved_facts_are_exposed_for_generation():
    org_id, other_org = uuid4(), uuid4()
    client_id = uuid4()
    with _session() as session:
        session.add_all([
            Org(id=org_id, name="A", slug="agency-a"),
            Org(id=other_org, name="B", slug="agency-b"),
            Client(id=client_id, org_id=org_id, name="Dental", slug="dental", category="dental"),
            ClientFact(org_id=org_id, client_id=client_id, key="phone", value="123", value_type="text", source_kind="human", status="approved"),
            ClientFact(org_id=org_id, client_id=client_id, key="price", value="99", value_type="text", source_kind="search", status="proposed"),
            ClientFact(org_id=other_org, client_id=client_id, key="secret", value="x", value_type="text", source_kind="human", status="approved"),
        ])
        session.commit()
        facts = ClientFactRepository(session, org_id).approved_for_client(client_id)
        assert [fact.key for fact in facts] == ["phone"]
