"""add confirmations table

Revision ID: 20260511_000003
Revises: 20260503_000002
Create Date: 2026-05-11 00:00:03
"""

from alembic import op
import sqlalchemy as sa


revision = "20260511_000003"
down_revision = "20260503_000002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "confirmations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "report_id", name="uq_confirmations_user_report"),
    )
    op.create_index("ix_confirmations_created_at", "confirmations", ["created_at"], unique=False)
    op.create_index("ix_confirmations_report_id", "confirmations", ["report_id"], unique=False)
    op.create_index("ix_confirmations_user_id", "confirmations", ["user_id"], unique=False)


def downgrade():
    op.drop_index("ix_confirmations_user_id", table_name="confirmations")
    op.drop_index("ix_confirmations_report_id", table_name="confirmations")
    op.drop_index("ix_confirmations_created_at", table_name="confirmations")
    op.drop_table("confirmations")
