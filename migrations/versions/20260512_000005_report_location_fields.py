"""add structured report location fields

Revision ID: 20260512_000005
Revises: 20260512_000004
Create Date: 2026-05-12 00:00:05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260512_000005"
down_revision = "20260512_000004"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("reports") as batch_op:
        batch_op.add_column(sa.Column("street_address", sa.String(length=255), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("suburb", sa.String(length=120), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("postcode", sa.String(length=10), nullable=False, server_default=""))
        batch_op.create_index("ix_reports_street_address", ["street_address"], unique=False)
        batch_op.create_index("ix_reports_suburb", ["suburb"], unique=False)
        batch_op.create_index("ix_reports_postcode", ["postcode"], unique=False)

    op.execute("UPDATE reports SET street_address = COALESCE(location, '')")


def downgrade():
    with op.batch_alter_table("reports") as batch_op:
        batch_op.drop_index("ix_reports_postcode")
        batch_op.drop_index("ix_reports_suburb")
        batch_op.drop_index("ix_reports_street_address")
        batch_op.drop_column("postcode")
        batch_op.drop_column("suburb")
        batch_op.drop_column("street_address")
