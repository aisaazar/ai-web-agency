"""Tenant-scoped repository for client records.

Repositories receive an existing Session and never commit, rollback, or close it.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from agency.db.models import Client


class ClientRepository:
    def __init__(self, session: Session, org_id):
        self.session = session
        self.org_id = org_id

    def get(self, client_id):
        return self.session.scalar(
            select(Client).where(Client.id == client_id, Client.org_id == self.org_id)
        )

    def get_by_slug(self, slug: str):
        return self.session.scalar(
            select(Client).where(Client.slug == slug, Client.org_id == self.org_id)
        )

    def list(self) -> list[Client]:
        return list(
            self.session.scalars(
                select(Client).where(Client.org_id == self.org_id).order_by(Client.name)
            )
        )

    def add(self, client: Client) -> Client:
        if client.org_id != self.org_id:
            raise ValueError("client org_id does not match repository org_id")
        self.session.add(client)
        self.session.flush()
        return client
