"""add acquisition prospects

Revision ID: 0f2a9f6d7b11
Revises: b09f3c9ff3b0
"""
from alembic import op
import sqlalchemy as sa


revision = "0f2a9f6d7b11"
down_revision = "b09f3c9ff3b0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "prospects",
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("country", sa.String(8), nullable=False),
        sa.Column("website_url", sa.String(500), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("source_kind", sa.String(40), nullable=False),
        sa.Column("contactability", sa.String(32), nullable=False),
        sa.Column("website_status", sa.String(16), nullable=False),
        sa.Column("fit_score", sa.Integer(), nullable=False),
        sa.Column("opportunity_score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_prospects_org_id", "prospects", ["org_id"])


def downgrade():
    op.drop_index("ix_prospects_org_id", table_name="prospects")
    op.drop_table("prospects")
