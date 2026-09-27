"""Per-client LLM spend budgets."""

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agency.db.base import Base, OrgScopedMixin, TimestampMixin, UUIDMixin


class ClientLLMBudget(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "client_llm_budgets"
    __table_args__ = (UniqueConstraint("org_id", "client_id", name="uq_client_llm_budget"),)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    budget_micros: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
