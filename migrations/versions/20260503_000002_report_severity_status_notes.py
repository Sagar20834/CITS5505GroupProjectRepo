"""add report severity and status notes

Revision ID: 20260503_000002
Revises: 20260416_000001
Create Date: 2026-05-03 00:00:02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260503_000002"
down_revision = "20260416_000001"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("reports") as batch_op:
        batch_op.add_column(sa.Column("severity", sa.String(length=20), nullable=False, server_default="Medium"))
        batch_op.create_index("ix_reports_severity", ["severity"], unique=False)

    op.create_table(
        "report_status_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("old_status", sa.String(length=30), nullable=False),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_report_status_notes_admin_id", "report_status_notes", ["admin_id"], unique=False)
    op.create_index("ix_report_status_notes_created_at", "report_status_notes", ["created_at"], unique=False)
    op.create_index("ix_report_status_notes_report_id", "report_status_notes", ["report_id"], unique=False)


def downgrade():
    op.drop_index("ix_report_status_notes_report_id", table_name="report_status_notes")
    op.drop_index("ix_report_status_notes_created_at", table_name="report_status_notes")
    op.drop_index("ix_report_status_notes_admin_id", table_name="report_status_notes")
    op.drop_table("report_status_notes")

    with op.batch_alter_table("reports") as batch_op:
        batch_op.drop_index("ix_reports_severity")
        batch_op.drop_column("severity")
