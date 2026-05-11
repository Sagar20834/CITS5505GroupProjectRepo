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

    pothole_report = Report()
    pothole_report.issue_type = "Pothole"
    pothole_report.location = "Hay Street, Perth CBD"
    pothole_report.description = "A deep pothole has opened beside the turning lane and is affecting cars during peak hour."
    pothole_report.status = "Reported"
    pothole_report.reporter_id = resident.id

    flooding_report = Report()
    flooding_report.issue_type = "Flooding"
    flooding_report.location = "Canning Highway, South Perth"
    flooding_report.description = (
        "Water remains pooled along the shoulder after rain and is forcing cyclists into traffic."
    )
    flooding_report.status = "Under Review"
    flooding_report.is_anonymous = True
    flooding_report.reporter_id = resident.id

    broken_road_report = Report()
    broken_road_report.issue_type = "Broken Road"
    broken_road_report.location = "Great Eastern Highway"
    broken_road_report.description = (
        "The surface is fragmented across a short stretch and vehicles are bouncing through the section."
    )
    broken_road_report.status = "Fixed"
    broken_road_report.reporter_id = admin.id

    sample_reports = [pothole_report, flooding_report, broken_road_report]

    db.session.add_all(sample_reports)
    db.session.commit()
    click.echo("Demo users and reports created.")
