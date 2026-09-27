from uuid import uuid4

import pytest

from agency.db.base import Base
from agency.db.models import Artifact, Org
from agency.db.session import create_session_factory
from agency.services.artifact_service import create_revision


def _session():
    factory = create_session_factory("sqlite:///:memory:")
    Base.metadata.create_all(factory.kw["bind"])
    return factory()


def test_revision_creates_new_active_artifact_and_preserves_source_payload():
    org_id = uuid4()
    with _session() as session:
        session.add(Org(id=org_id, name="A", slug="agency-a"))
        source = Artifact(
            org_id=org_id,
            artifact_type="content_model",
            schema_version="1.0.0",
            payload_json={"headline": "Original"},
        )
        session.add(source)
        session.commit()

        revision = create_revision(
            session,
            org_id=org_id,
            source=source,
            payload_json={"headline": "Updated"},
            schema_version="1.0.0",
        )
        session.commit()

        session.refresh(source)
        assert source.payload_json == {"headline": "Original"}
        assert source.is_active is False
        assert revision.revision == 2
        assert revision.input_artifact_id == source.id
        assert revision.is_active is True


def test_revision_rejects_wrong_tenant_or_schema():
    org_a, org_b = uuid4(), uuid4()
    with _session() as session:
        session.add_all([
            Org(id=org_a, name="A", slug="agency-a"),
            Org(id=org_b, name="B", slug="agency-b"),
        ])
        source = Artifact(
            org_id=org_a,
            artifact_type="business_facts",
            schema_version="1.0.0",
            payload_json={"x": 1},
        )
        session.add(source)
        session.commit()
        with pytest.raises(ValueError, match="does not belong"):
            create_revision(session, org_id=org_b, source=source, payload_json={"x": 2}, schema_version="1.0.0")
        with pytest.raises(ValueError, match="schema version"):
            create_revision(session, org_id=org_a, source=source, payload_json={"x": 2}, schema_version="2.0.0")
