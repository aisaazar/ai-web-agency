"""Pydantic contracts for the customer-facing assistant."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    consent: bool


class ConversationCreateOut(BaseModel):
    conversation_id: UUID
    consent_notice: str


class AgentMessageIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=5000)


class AgentMessageOut(BaseModel):
    conversation_id: UUID
    role: str
    message: str
    escalated: bool
    contact_phone: str | None
    contact_email: str | None


class ConversationMessageOut(BaseModel):
    role: str
    message: str
    escalated: bool
    created_at: datetime
