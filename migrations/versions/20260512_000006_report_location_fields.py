"""add structured report location fields

Revision ID: 20260512_000006
Revises: 20260512_000005
Create Date: 2026-05-12 00:00:05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260512_000006"
down_revision = "20260512_000005"
branch_labels = None
depends_on = None


reports_table = sa.table(
    "reports",
    sa.column("id", sa.Integer),
    sa.column("location", sa.String),
    sa.column("street_address", sa.String),
    sa.column("suburb", sa.String),
    sa.column("postcode", sa.String),
)


def _parse_location(location):
    location = " ".join((location or "").split())
    if not location:
        return "", "", ""

    if "," not in location:
        return location, "", ""

    street_address, locality = [part.strip() for part in location.split(",", 1)]
    locality_parts = locality.split()

    if locality_parts and locality_parts[-1].isdigit() and len(locality_parts[-1]) == 4:
        postcode = locality_parts[-1]
        suburb = " ".join(locality_parts[:-1])
    else:
        suburb = locality
        postcode = ""

    return street_address, suburb, postcode


def _backfill_location_parts(connection):
    reports = connection.execute(
        sa.select(
            reports_table.c.id,
            reports_table.c.location,
            reports_table.c.street_address,
            reports_table.c.suburb,
            reports_table.c.postcode,
        )
    ).mappings().all()

    for report in reports:
        street_address, suburb, postcode = _parse_location(report["location"])
        if not street_address:
            continue

        values = {}
        if not report["street_address"] or report["street_address"] == report["location"]:
            values["street_address"] = street_address
        if not report["suburb"] and suburb:
            values["suburb"] = suburb
        if not report["postcode"] and postcode:
            values["postcode"] = postcode

        if values:
            connection.execute(
                reports_table.update()
                .where(reports_table.c.id == report["id"])
                .values(**values)
            )


def upgrade():
    with op.batch_alter_table("reports") as batch_op:
        batch_op.add_column(sa.Column("street_address", sa.String(length=255), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("suburb", sa.String(length=120), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("postcode", sa.String(length=10), nullable=False, server_default=""))
        batch_op.create_index("ix_reports_street_address", ["street_address"], unique=False)
        batch_op.create_index("ix_reports_suburb", ["suburb"], unique=False)
        batch_op.create_index("ix_reports_postcode", ["postcode"], unique=False)

    _backfill_location_parts(op.get_bind())


def downgrade():
    with op.batch_alter_table("reports") as batch_op:
        batch_op.drop_index("ix_reports_postcode")
        batch_op.drop_index("ix_reports_suburb")
        batch_op.drop_index("ix_reports_street_address")
        batch_op.drop_column("postcode")
        batch_op.drop_column("suburb")
        batch_op.drop_column("street_address")
