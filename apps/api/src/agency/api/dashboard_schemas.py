"""Typed dashboard response contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DashboardCounts(BaseModel):
    clients: int
    artifacts: int
    deployments: int
    new_leads: int


class DashboardClientOut(BaseModel):
    id: UUID
    name: str
    category: str
    state: str
    updated_at: datetime
    live_url: str | None = None
    current_build_hash: str | None = None


class DashboardArtifactOut(BaseModel):
    id: UUID
    type: str
    revision: int
    status: str
    build_hash: str | None = None
    updated_at: datetime


class DashboardDeploymentOut(BaseModel):
    id: UUID
    client: str
    provider: str
    environment: str
    status: str
    url: str | None = None
    created_at: datetime


class DashboardLeadOut(BaseModel):
    id: UUID
    client: str
    name: str
    status: str
    email: str
    received_at: datetime


class DashboardOverviewOut(BaseModel):
    org_id: UUID
    counts: DashboardCounts
    clients: list[DashboardClientOut]
    artifacts: list[DashboardArtifactOut]
    deployments: list[DashboardDeploymentOut]
    leads: list[DashboardLeadOut]
