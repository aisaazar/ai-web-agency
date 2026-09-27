"""Workflow persistence kept separate from the core model module."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from agency.db.base import Base, OrgScopedMixin, TimestampMixin, UUIDMixin


class PipelineRun(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "pipeline_runs"
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    error: Mapped[str | None] = mapped_column(String(2000))
