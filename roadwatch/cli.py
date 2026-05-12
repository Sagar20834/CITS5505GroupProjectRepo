import click
from flask.cli import with_appcontext

from .extensions import db
from .models import Report, User


@click.command("seed-demo")
@with_appcontext
def seed_demo_command():
    if User.query.count() or Report.query.count():
        click.echo("Database already contains data. Seed skipped.")
        return

    admin = User()
    admin.username = "admin"
    admin.email = "admin@roadwatch.local"
    admin.is_admin = True
    admin.set_password("AdminPass123")

    resident = User()
    resident.username = "perthresident"
    resident.email = "resident@roadwatch.local"
    resident.set_password("ResidentPass123")

    db.session.add_all([admin, resident])
    db.session.flush()

    sample_reports = [
        Report(
            issue_type="Pothole",
            street_address="Hay Street",
            suburb="Perth CBD",
            postcode="6000",
            description="A deep pothole has opened beside the turning lane and is affecting cars during peak hour.",
            status="Reported",
            severity="High",
            moderation_status="Approved",
            reporter_id=resident.id,
        ),
        Report(
            issue_type="Flooding",
            street_address="Canning Highway",
            suburb="South Perth",
            postcode="6151",
            description="Water remains pooled along the shoulder after rain and is forcing cyclists into traffic.",
            status="Under Review",
            severity="Urgent",
            moderation_status="Approved",
            is_anonymous=True,
            reporter_id=resident.id,
        ),
        Report(
            issue_type="Broken Road",
            street_address="Great Eastern Highway",
            suburb="Rivervale",
            postcode="6103",
            description="The surface is fragmented across a short stretch and vehicles are bouncing through the section.",
            status="Fixed",
            severity="Medium",
            moderation_status="Approved",
            reporter_id=admin.id,
        ),
    ]

    db.session.add_all(sample_reports)
    db.session.commit()
    click.echo("Demo users and reports created.")
