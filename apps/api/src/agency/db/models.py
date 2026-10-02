"""Core persistence models for the v1 tenancy and delivery boundary."""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from agency.db.base import Base, OrgScopedMixin, SlugMixin, TimestampMixin, UUIDMixin


class Org(Base, UUIDMixin, TimestampMixin, SlugMixin):
    __tablename__ = "orgs"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    required_approvals: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["FACTS", "RESEARCH", "CONTENT", "PUBLISH"])
    default_jurisdiction: Mapped[str] = mapped_column(String(8), default="DE")
    llm_budget_micros: Mapped[int] = mapped_column(Integer, default=0)


class Client(Base, UUIDMixin, TimestampMixin, OrgScopedMixin, SlugMixin):
    __tablename__ = "clients"
    __table_args__ = (UniqueConstraint("org_id", "slug", name="uq_clients_org_slug"),)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(8), default="DE")
    locale: Mapped[str] = mapped_column(String(16), default="de-DE")
    existing_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), default="active")


class ClientFact(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "client_facts"
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(150), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(500))
    confidence: Mapped[float | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(16), default="proposed")
    approved_by: Mapped[str | None] = mapped_column(String(255))


class AgentRun(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "agent_runs"
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    agent: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"))
    output_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"))
    error: Mapped[str | None] = mapped_column(Text)


class LLMInvocation(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "llm_invocations"
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    agent_run_id: Mapped[str | None] = mapped_column(ForeignKey("agent_runs.id"))
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_micros: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class Artifact(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "artifacts"
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    build_hash: Mapped[str | None] = mapped_column(String(128))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    input_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("artifacts.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Approval(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "approvals"
    artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), nullable=False)
    gate: Mapped[str] = mapped_column(String(32), nullable=False)
    decision: Mapped[str] = mapped_column(String(16), nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text)
    approved_by: Mapped[str | None] = mapped_column(String(255))


class Site(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "sites"
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False)
    template_id: Mapped[str] = mapped_column(String(100), nullable=False)
    design_preset_id: Mapped[str] = mapped_column(String(100), nullable=False)
    current_build_hash: Mapped[str | None] = mapped_column(String(128))
    live_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), default="draft")


class SiteVersion(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "site_versions"
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id"), nullable=False)
    build_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    content_artifact_id: Mapped[str] = mapped_column(ForeignKey("artifacts.id"), nullable=False)
    content_schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    template_version: Mapped[str] = mapped_column(String(64), nullable=False)
    design_preset_id: Mapped[str] = mapped_column(String(100), nullable=False)


class BuildValidation(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "build_validations"
    site_version_id: Mapped[str] = mapped_column(ForeignKey("site_versions.id"), nullable=False)
    check_name: Mapped[str] = mapped_column(String(64), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    detail_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Deploy(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "deploys"
    site_version_id: Mapped[str] = mapped_column(ForeignKey("site_versions.id"), nullable=False)
    environment: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500))


class Prospect(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "prospects"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    city: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(8), default="DE", nullable=False)
    website_url: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_kind: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    contactability: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    website_status: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    fit_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opportunity_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="new", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class LeadSubmission(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "lead_submissions"
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id"), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), nullable=False, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(80))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    consent_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    spam_score: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="new", nullable=False)
    utm_json: Mapped[dict | None] = mapped_column(JSON)


class LeadEvent(Base, UUIDMixin, TimestampMixin, OrgScopedMixin):
    __tablename__ = "lead_events"
    lead_submission_id: Mapped[str] = mapped_column(ForeignKey("lead_submissions.id"), nullable=False, index=True)
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
