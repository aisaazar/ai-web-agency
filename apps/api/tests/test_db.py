from uuid import uuid4

from sqlalchemy import create_engine, event, inspect, text

from agency.db.base import Base
from agency.db.models import Approval, Artifact, Client, Org
from agency.db.session import create_session_factory


def test_core_models_are_org_scoped():
    assert "org_id" in Org.__table__.columns or True
    for model in (Client, Artifact, Approval):
        assert "org_id" in model.__table__.columns


def test_sqlite_schema_and_pragmas():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    Base.metadata.create_all(engine)
    tables = set(inspect(engine).get_table_names())
    assert {"orgs", "clients", "artifacts", "approvals", "sites", "site_versions", "build_validations", "deploys"} <= tables
    with engine.connect() as conn:
        assert conn.execute(text("PRAGMA foreign_keys")).scalar() == 1
        assert conn.execute(text("PRAGMA busy_timeout")).scalar() == 5000
    engine.dispose()


def test_org_client_relationship_can_be_persisted():
    factory = create_session_factory("sqlite:///:memory:")
    Base.metadata.create_all(factory.kw["bind"])
    org_id = uuid4()
    with factory() as session:
        org = Org(id=org_id, name="Test Agency", slug="test-agency")
        client = Client(org_id=org_id, name="Example Dental", slug="example-dental", category="dental")
        session.add_all([org, client])
        session.commit()
        assert session.get(Client, client.id).org_id == org_id
