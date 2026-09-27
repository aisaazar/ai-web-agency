"""Customer-agent conversation persistence models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agency.db.base import Base, OrgScopedMixin, TimestampMixin, UUIDMixin


class Conversation(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "conversations"
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    visitor_ref: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", nullable=False)
    escalated: Mapped[bool] = mapped_column(default=False, nullable=False)


class ConversationMessage(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "conversation_messages"
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content_redacted: Mapped[str] = mapped_column(Text, nullable=False)
    escalated: Mapped[bool] = mapped_column(default=False, nullable=False)
