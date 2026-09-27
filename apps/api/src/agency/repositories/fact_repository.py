"""Tenant-scoped client fact access."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import ClientFact


class ClientFactRepository:
    def __init__(self, session: Session, org_id):
        self.session = session
        self.org_id = org_id

    def approved_for_client(self, client_id) -> list[ClientFact]:
        return list(
            self.session.scalars(
                select(ClientFact)
                .where(
                    ClientFact.org_id == self.org_id,
                    ClientFact.client_id == client_id,
                    ClientFact.status == "approved",
                )
                .order_by(ClientFact.key)
            )
        )

    def add(self, fact: ClientFact) -> ClientFact:
        if fact.org_id != self.org_id:
            raise ValueError("fact org_id does not match repository org_id")
        self.session.add(fact)
        self.session.flush()
        return fact
