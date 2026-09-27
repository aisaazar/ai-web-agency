from uuid import uuid4

from agency.db.base import Base
from agency.db.models import Client, Org
from agency.db.session import create_session_factory
from agency.repositories import ClientRepository


def _session():
    factory = create_session_factory("sqlite:///:memory:")
    Base.metadata.create_all(factory.kw["bind"])
    return factory()


def test_client_repository_is_tenant_scoped():
    org_a, org_b = uuid4(), uuid4()
    with _session() as session:
        session.add_all([
            Org(id=org_a, name="A", slug="agency-a"),
            Org(id=org_b, name="B", slug="agency-b"),
            Client(org_id=org_a, name="Alpha", slug="alpha", category="dental"),
            Client(org_id=org_b, name="Beta", slug="beta", category="dental"),
        ])
        session.commit()
        repo = ClientRepository(session, org_a)
        assert [client.slug for client in repo.list()] == ["alpha"]
        assert repo.get_by_slug("beta") is None


def test_repository_does_not_commit_and_rejects_cross_tenant_add():
    org_a, org_b = uuid4(), uuid4()
    with _session() as session:
        session.add_all([Org(id=org_a, name="A", slug="agency-a"), Org(id=org_b, name="B", slug="agency-b")])
        session.commit()
        repo = ClientRepository(session, org_a)
        client = Client(org_id=org_b, name="Beta", slug="beta", category="dental")
        try:
            repo.add(client)
        except ValueError:
            pass
        else:
            raise AssertionError("cross-tenant client must be rejected")
        assert client not in session.new
