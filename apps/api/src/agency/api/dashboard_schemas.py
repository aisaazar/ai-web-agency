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


class DashboardLLMClientCostOut(BaseModel):
    client_id: UUID
    client_name: str
    budget_micros: int
    spent_micros: int


class DashboardLLMCostOut(BaseModel):
    org_id: UUID
    budget_micros: int
    spent_micros: int
    clients: list[DashboardLLMClientCostOut]


class DashboardOverviewOut(BaseModel):
    org_id: UUID
    counts: DashboardCounts
    clients: list[DashboardClientOut]
    artifacts: list[DashboardArtifactOut]
    deployments: list[DashboardDeploymentOut]
    leads: list[DashboardLeadOut]


class DashboardClientDetailArtifactOut(BaseModel):
    id: UUID
    type: str
    revision: int
    status: str
    build_hash: str | None = None
    updated_at: datetime


class DashboardApprovalOut(BaseModel):
    id: UUID
    artifact_id: UUID
    gate: str
    decision: str
    feedback: str | None = None
    approved_by: str | None = None
    created_at: datetime


class DashboardSiteVersionOut(BaseModel):
    id: UUID
    build_hash: str
    content_artifact_id: UUID
    template_version: str
    design_preset_id: str
    created_at: datetime


class DashboardClientDetailOut(BaseModel):
    org_id: UUID
    client: DashboardClientOut
    artifacts: list[DashboardClientDetailArtifactOut]
    approvals: list[DashboardApprovalOut]
    site_versions: list[DashboardSiteVersionOut]
    deployments: list[DashboardDeploymentOut]
