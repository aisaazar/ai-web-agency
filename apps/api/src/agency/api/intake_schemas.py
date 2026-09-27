"""Admin-side intake schemas."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IntakeFactIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=150)
    value: str = Field(min_length=1, max_length=5000)
    value_type: str = Field(default="text", min_length=1, max_length=32)
    source_kind: str = Field(default="client", min_length=1, max_length=32)
    source_ref: str | None = Field(default=None, max_length=500)
    confidence: float | None = Field(default=None, ge=0, le=1)


class IntakeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: UUID
    client_name: str = Field(min_length=1, max_length=200)
    client_slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=120)
    category: str = Field(min_length=1, max_length=100)
    jurisdiction: str = Field(default="DE", min_length=2, max_length=8)
    locale: str = Field(default="de-DE", min_length=5, max_length=16)
    existing_url: str | None = Field(default=None, max_length=500)
    facts: list[IntakeFactIn] = Field(default_factory=list, max_length=100)


class IntakeResponse(BaseModel):
    client_id: UUID
    pipeline_run_id: UUID
    state: str
    fact_count: int
