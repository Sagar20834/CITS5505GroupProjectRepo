"""add report moderation status

Revision ID: 20260512_000004
Revises: 20260511_000003
Create Date: 2026-05-12 00:00:02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260512_000004"
down_revision = "20260511_000003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "reports",
        sa.Column(
            "moderation_status",
            sa.String(length=30),
            nullable=False,
            server_default="Approved",
        ),
    )
    op.create_index("ix_reports_moderation_status", "reports", ["moderation_status"], unique=False)


def downgrade():
    op.drop_index("ix_reports_moderation_status", table_name="reports")
    op.drop_column("reports", "moderation_status")
