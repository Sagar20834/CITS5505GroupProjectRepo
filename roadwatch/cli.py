from datetime import datetime, timezone

import click
from flask.cli import with_appcontext

from .extensions import db
from .models import Comment, Confirmation, Report, ReportStatusNote, User


def _utc_datetime(year, month, day, hour=8, minute=0):
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _build_demo_report(
    *,
    key,
    issue_type,
    location,
    severity,
    status,
    description,
    created_at,
    reporter_id=None,
    is_anonymous=False,
    image_url=None,
):
    report = Report()
    report._demo_key = key
    report.issue_type = issue_type
    report.location = location
    report.severity = severity
    report.status = status
    report.description = description
    report.created_at = created_at
    report.updated_at = created_at
    report.reporter_id = reporter_id
    report.is_anonymous = is_anonymous
    report.image_url = image_url
    return report


def _build_comment(*, report_id, author_id, body):
    comment = Comment()
    comment.report_id = report_id
    comment.author_id = author_id
    comment.body = body
    return comment


def _build_confirmation(*, report_id, user_id):
    confirmation = Confirmation()
    confirmation.report_id = report_id
    confirmation.user_id = user_id
    return confirmation


def _build_status_note(*, report_id, admin_id, old_status, new_status, note):
    status_note = ReportStatusNote()
    status_note.report_id = report_id
    status_note.admin_id = admin_id
    status_note.old_status = old_status
    status_note.new_status = new_status
    status_note.note = note
    return status_note


def _seed_demo_data():
    current_year = datetime.now(timezone.utc).year

    admin = User()
    admin.username = "admin"
    admin.email = "admin@roadwatch.local"
    admin.is_admin = True
    admin.set_password("AdminPass123")

    resident = User()
    resident.username = "perthresident"
    resident.email = "resident@roadwatch.local"
    resident.set_password("ResidentPass123")

    commuter = User()
    commuter.username = "citycommuter"
    commuter.email = "commuter@roadwatch.local"
    commuter.set_password("CommuterPass123")

    cyclist = User()
    cyclist.username = "perthcyclist"
    cyclist.email = "cyclist@roadwatch.local"
    cyclist.set_password("CyclistPass123")

    db.session.add_all([admin, resident, commuter, cyclist])
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
    db.session.flush()

    report_lookup = {report._demo_key: report for report in sample_reports}

    demo_comments = [
        _build_comment(
            report_id=report_lookup["hay-pothole"].id,
            author_id=commuter.id,
            body="I drove through this yesterday and it is definitely getting deeper near the lane marking.",
        ),
        _build_comment(
            report_id=report_lookup["hay-pothole"].id,
            author_id=admin.id,
            body="Thanks for the extra context. I have flagged this one for a maintenance inspection.",
        ),
        _build_comment(
            report_id=report_lookup["canning-flooding"].id,
            author_id=resident.id,
            body="This shoulder floods after even light rain now, especially around the morning commute.",
        ),
        _build_comment(
            report_id=report_lookup["albany-pothole"].id,
            author_id=cyclist.id,
            body="Buses are still swerving around it, so cyclists are being pushed wide in peak hour.",
        ),
        _build_comment(
            report_id=report_lookup["tonkin-broken"].id,
            author_id=admin.id,
            body="Heavy vehicle damage has been confirmed and the site has been sent for urgent review.",
        ),
    ]

    demo_confirmations = [
        _build_confirmation(report_id=report_lookup["hay-pothole"].id, user_id=commuter.id),
        _build_confirmation(report_id=report_lookup["hay-pothole"].id, user_id=cyclist.id),
        _build_confirmation(report_id=report_lookup["canning-flooding"].id, user_id=resident.id),
        _build_confirmation(report_id=report_lookup["canning-flooding"].id, user_id=commuter.id),
        _build_confirmation(report_id=report_lookup["albany-pothole"].id, user_id=cyclist.id),
        _build_confirmation(report_id=report_lookup["tonkin-broken"].id, user_id=resident.id),
        _build_confirmation(report_id=report_lookup["tonkin-broken"].id, user_id=cyclist.id),
        _build_confirmation(report_id=report_lookup["roe-pothole"].id, user_id=resident.id),
    ]

    demo_status_notes = [
        _build_status_note(
            report_id=report_lookup["hay-crack"].id,
            admin_id=admin.id,
            old_status="Reported",
            new_status="Under Review",
            note="Inspection requested because repeated cracking has now spread across most of the lane.",
        ),
        _build_status_note(
            report_id=report_lookup["great-eastern-broken"].id,
            admin_id=admin.id,
            old_status="Under Review",
            new_status="Fixed",
            note="Temporary resurfacing was completed and the damaged section has been reopened.",
        ),
        _build_status_note(
            report_id=report_lookup["marmion-pothole"].id,
            admin_id=admin.id,
            old_status="Under Review",
            new_status="Fixed",
            note="Emergency crew patched the hazard after reports of tyre damage over the weekend.",
        ),
        _build_status_note(
            report_id=report_lookup["tonkin-broken"].id,
            admin_id=admin.id,
            old_status="Reported",
            new_status="Under Review",
            note="Escalated because freight traffic is amplifying the breakup and spreading loose debris.",
        ),
    ]

    db.session.add_all(demo_comments)
    db.session.add_all(demo_confirmations)
    db.session.add_all(demo_status_notes)
    db.session.commit()


@click.command("seed-demo")
@with_appcontext
def seed_demo_command():
    if User.query.count() or Report.query.count():
        click.echo("Database already contains data. Seed skipped.")
        return

    _seed_demo_data()
    click.echo("Demo users and reports created with varied issue types, statuses, and hotspots.")


@click.command("reset-demo")
@click.option("--yes", is_flag=True, help="Reset local app data without an interactive confirmation prompt.")
@with_appcontext
def reset_demo_command(yes):
    if not yes and not click.confirm("This will delete all current users, reports, comments, confirmations, and status notes. Continue?"):
        click.echo("Reset cancelled.")
        return

    db.session.query(Comment).delete()
    db.session.query(Confirmation).delete()
    db.session.query(ReportStatusNote).delete()
    db.session.query(Report).delete()
    db.session.query(User).delete()
    db.session.commit()

    _seed_demo_data()
    click.echo("Local app data was reset and fresh demo data was loaded.")
