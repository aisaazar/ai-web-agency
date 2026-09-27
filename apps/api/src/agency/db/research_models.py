"""Research execution and evidence tables."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from agency.db.base import Base, OrgScopedMixin, TimestampMixin, UUIDMixin


class ResearchRun(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "research_runs"
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"))
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    query_plan_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")


class ResearchSource(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "research_sources"
    research_run_id: Mapped[str] = mapped_column(ForeignKey("research_runs.id"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
