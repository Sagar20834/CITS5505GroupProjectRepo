"""add notifications table

Revision ID: 20260516_000007
Revises: 20260512_000006
Create Date: 2026-05-16 00:00:07
"""

from alembic import op
import sqlalchemy as sa


revision = "20260516_000007"
down_revision = "20260512_000006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=True),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("link_url", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"], unique=False)
    op.create_index("ix_notifications_report_id", "notifications", ["report_id"], unique=False)
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)


def downgrade():
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_report_id", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_table("notifications")
