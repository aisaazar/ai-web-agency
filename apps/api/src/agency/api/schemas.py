"""Pydantic schemas for public API boundaries."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LeadSubmissionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    site_id: UUID
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+$", max_length=320)
    phone: str | None = Field(default=None, max_length=80)
    message: str = Field(min_length=1, max_length=5000)
    consent: bool
    website: str = Field(default="", max_length=200)
    form_started_at: datetime | None = None
    utm: dict[str, str] | None = None


class LeadSubmissionOut(BaseModel):
    id: UUID
    status: str
    received_at: datetime


LeadStatus = Literal["new", "contacted", "qualified", "won", "lost"]


class LeadStatusUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: LeadStatus
    actor: str = Field(min_length=1, max_length=255)
    note: str | None = Field(default=None, max_length=2000)


class LeadEventOut(BaseModel):
    id: UUID
    from_status: str | None
    to_status: str
    actor: str
    note: str | None
    created_at: datetime
