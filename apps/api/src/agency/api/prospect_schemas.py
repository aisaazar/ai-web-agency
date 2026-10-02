"""Schemas for the acquisition prospect workspace."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ProspectStatus = Literal[
    "new", "contacted", "qualified", "converted", "dismissed"
]
WebsiteStatus = Literal["missing", "poor", "unknown", "good"]


class ProspectCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: UUID
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    city: str | None = Field(default=None, max_length=120)
    country: str = Field(default="DE", min_length=2, max_length=8)
    website_url: str | None = Field(default=None, max_length=500)
    source_url: str | None = Field(default=None, max_length=500)
    source_kind: str = Field(default="manual", min_length=1, max_length=40)
    contactability: str = Field(default="unknown", max_length=32)
    website_status: WebsiteStatus = "unknown"
    notes: str | None = Field(default=None, max_length=4000)


class ProspectOut(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    category: str
    city: str | None
    country: str
    website_url: str | None
    source_url: str | None
    source_kind: str
    contactability: str
    website_status: WebsiteStatus
    fit_score: int
    opportunity_score: int
    status: ProspectStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ProspectStatusUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ProspectStatus
    note: str | None = Field(default=None, max_length=2000)
