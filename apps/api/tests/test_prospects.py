from uuid import uuid4

from agency.api.prospect_schemas import ProspectCreateIn, ProspectStatusUpdateIn
from agency.db.base import Base
from agency.db.models import Org, Prospect
from agency.db.session import create_session_factory
from agency.services.prospect_service import (
    create_prospect,
    list_prospects,
    update_prospect_status,
)


def _session():
    factory = create_session_factory("sqlite:///:memory:")
    Base.metadata.create_all(factory.kw["bind"])
    return factory()


def _payload(org_id):
    return ProspectCreateIn(
        org_id=org_id,
        name="Example Praxis",
        category="dental",
        city="Nürnberg",
        website_url=None,
        source_url="https://example.org/directory/praxis",
        source_kind="public_directory",
        contactability="email+phone",
        website_status="missing",
    )


def test_create_prospect_is_deterministically_prioritized():
    org_id = uuid4()
    with _session() as session:
        session.add(Org(id=org_id, name="A", slug="agency-a"))
        session.commit()
        created = create_prospect(session, _payload(org_id), actor="operator")
        assert created.status == "new"
        assert created.website_status == "missing"
        assert created.fit_score == 60
        assert created.opportunity_score == 85


def test_prospect_listing_is_tenant_scoped():
    org_a, org_b = uuid4(), uuid4()
    with _session() as session:
        session.add_all([
            Org(id=org_a, name="A", slug="agency-a"),
            Org(id=org_b, name="B", slug="agency-b"),
        ])
        session.commit()
        create_prospect(session, _payload(org_a), actor="operator")
        create_prospect(session, _payload(org_b), actor="operator")
        rows = list_prospects(session, org_id=org_a)
        assert len(rows) == 1
        assert rows[0].org_id == org_a

def test_status_update_records_new_sales_state():
    org_id = uuid4()
    with _session() as session:
        session.add(Org(id=org_id, name="A", slug="agency-a"))
        session.commit()
        created = create_prospect(session, _payload(org_id), actor="operator")
        updated = update_prospect_status(
            session,
            org_id=org_id,
            prospect_id=created.id,
            update=ProspectStatusUpdateIn(status="qualified", note="Ready for demo"),
            actor="operator",
        )
        assert updated.status == "qualified"
        stored = session.get(Prospect, created.id)
        assert stored.status == "qualified"
        assert stored.notes == "Ready for demo"
