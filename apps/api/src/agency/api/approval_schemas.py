"""Approval gate request/response models."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FactsApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: UUID
    client_id: UUID
    approved_by: str = Field(min_length=1, max_length=255)
    feedback: str | None = Field(default=None, max_length=5000)


class FactsApprovalResponse(BaseModel):
    client_id: UUID
    artifact_id: UUID
    pipeline_run_id: UUID
    state: str
    approved_fact_count: int
