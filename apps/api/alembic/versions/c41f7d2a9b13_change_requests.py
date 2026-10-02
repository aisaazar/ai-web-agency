"""add change_requests table for the client review loop

Revision ID: c41f7d2a9b13
Revises: b09f3c9ff3b0
Create Date: 2026-10-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c41f7d2a9b13"
down_revision: Union[str, Sequence[str], None] = "b09f3c9ff3b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the change_requests table."""
    op.create_table(
        "change_requests",
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("site_version_id", sa.Uuid(), nullable=False),
        sa.Column("build_hash", sa.String(length=128), nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("resulting_content_artifact_id", sa.Uuid(), nullable=True),
        sa.Column("resulting_build_hash", sa.String(length=128), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["resulting_content_artifact_id"], ["artifacts.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["site_version_id"], ["site_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("change_requests", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_change_requests_org_id"), ["org_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_change_requests_client_id"), ["client_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_change_requests_site_id"), ["site_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_change_requests_site_version_id"), ["site_version_id"], unique=False)


def downgrade() -> None:
    """Drop the change_requests table."""
    with op.batch_alter_table("change_requests", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_change_requests_site_version_id"))
        batch_op.drop_index(batch_op.f("ix_change_requests_site_id"))
        batch_op.drop_index(batch_op.f("ix_change_requests_client_id"))
        batch_op.drop_index(batch_op.f("ix_change_requests_org_id"))
    op.drop_table("change_requests")