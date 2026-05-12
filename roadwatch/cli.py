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
        _build_demo_report(
            key="hay-pothole",
            issue_type="Pothole",
            location="Hay Street, Perth CBD",
            severity="High",
            status="Reported",
            description="A deep pothole has opened beside the turning lane and is affecting cars during peak hour.",
            created_at=_utc_datetime(current_year, 1, 14, 7, 45),
            reporter_id=resident.id,
            image_url="https://loremflickr.com/1200/800/pothole,road?lock=101",
        ),
        _build_demo_report(
            key="hay-crack",
            issue_type="Crack",
            location="Hay Street, Perth CBD",
            severity="Medium",
            status="Under Review",
            description="Long cracks are spreading across the left lane and braking cars are bouncing through the section.",
            created_at=_utc_datetime(current_year, 1, 28, 9, 10),
            reporter_id=commuter.id,
            image_url="https://loremflickr.com/1200/800/cracked-road,street?lock=102",
        ),
        _build_demo_report(
            key="stgeorges-pothole",
            issue_type="Pothole",
            location="St Georges Terrace, Perth CBD",
            severity="Medium",
            status="Reported",
            description="A rough pothole near the taxi bay is forcing drivers to cut into the next lane at short notice.",
            created_at=_utc_datetime(current_year, 2, 7, 8, 35),
            reporter_id=commuter.id,
        ),
        _build_demo_report(
            key="canning-flooding",
            issue_type="Flooding",
            location="Canning Highway, South Perth",
            severity="High",
            status="Under Review",
            description="Water remains pooled along the shoulder after rain and is forcing cyclists into traffic.",
            created_at=_utc_datetime(current_year, 2, 3, 6, 55),
            reporter_id=cyclist.id,
            is_anonymous=True,
            image_url="https://loremflickr.com/1200/800/flooded-road,rain?lock=103",
        ),
        _build_demo_report(
            key="canning-sign",
            issue_type="Missing Sign",
            location="Canning Highway, South Perth",
            severity="Medium",
            status="Reported",
            description="A warning sign near the merge point is missing and drivers are cutting into the bike lane unexpectedly.",
            created_at=_utc_datetime(current_year, 2, 17, 8, 20),
            reporter_id=resident.id,
        ),
        _build_demo_report(
            key="great-eastern-broken",
            issue_type="Broken Road",
            location="Great Eastern Highway, Rivervale",
            severity="Urgent",
            status="Fixed",
            description="The surface is fragmented across a short stretch and vehicles are bouncing through the section.",
            created_at=_utc_datetime(current_year, 3, 2, 10, 30),
            reporter_id=admin.id,
            image_url="https://loremflickr.com/1200/800/damaged-road,highway?lock=104",
        ),
        _build_demo_report(
            key="leach-broken",
            issue_type="Broken Road",
            location="Leach Highway, Willetton",
            severity="High",
            status="Under Review",
            description="The road surface has broken up around a patched trench and traffic is drifting around the damaged area.",
            created_at=_utc_datetime(current_year, 3, 8, 13, 5),
            reporter_id=resident.id,
        ),
        _build_demo_report(
            key="albany-gravel",
            issue_type="Other",
            location="Albany Highway, Victoria Park",
            severity="Low",
            status="Reported",
            description="Loose gravel keeps spilling from the shoulder into the traffic lane after each windy afternoon.",
            created_at=_utc_datetime(current_year, 3, 19, 15, 5),
            reporter_id=commuter.id,
        ),
        _build_demo_report(
            key="albany-pothole",
            issue_type="Pothole",
            location="Albany Highway, Victoria Park",
            severity="High",
            status="Under Review",
            description="A pothole near the bus stop is widening and buses are swerving around it during school pickup.",
            created_at=_utc_datetime(current_year, 4, 5, 14, 25),
            reporter_id=resident.id,
            image_url="https://loremflickr.com/1200/800/pothole,street?lock=105",
        ),
        _build_demo_report(
            key="marmion-pothole",
            issue_type="Pothole",
            location="Marmion Avenue, Clarkson",
            severity="Urgent",
            status="Fixed",
            description="A large pothole near the median had been damaging tyres before emergency patching was completed.",
            created_at=_utc_datetime(current_year, 4, 9, 12, 15),
            reporter_id=admin.id,
            image_url="https://loremflickr.com/1200/800/road-repair,pothole?lock=106",
        ),
        _build_demo_report(
            key="wanneroo-crack",
            issue_type="Crack",
            location="Wanneroo Road, Balcatta",
            severity="Medium",
            status="Fixed",
            description="The cracked surface was causing steering wobble for motorcycles near the right-turn pocket.",
            created_at=_utc_datetime(current_year, 4, 13, 11, 40),
            reporter_id=admin.id,
        ),
        _build_demo_report(
            key="riverside-flooding",
            issue_type="Flooding",
            location="Riverside Drive, East Perth",
            severity="Medium",
            status="Reported",
            description="Drainage is blocked after light rain and water starts covering one lane beside the river wall.",
            created_at=_utc_datetime(current_year, 4, 29, 7, 15),
            reporter_id=cyclist.id,
        ),
        _build_demo_report(
            key="guildford-flooding",
            issue_type="Flooding",
            location="Guildford Road, Bayswater",
            severity="Medium",
            status="Reported",
            description="Water is repeatedly pooling near the curb after minor rain and buses are throwing spray onto the footpath.",
            created_at=_utc_datetime(current_year, 5, 2, 7, 5),
            reporter_id=resident.id,
        ),
        _build_demo_report(
            key="mitchell-sign",
            issue_type="Missing Sign",
            location="Mitchell Freeway Northbound Exit, Leederville",
            severity="Low",
            status="Fixed",
            description="Lane guidance signage at the exit was missing and motorists were braking late at the split.",
            created_at=_utc_datetime(current_year, 5, 4, 16, 50),
            reporter_id=admin.id,
        ),
        _build_demo_report(
            key="tonkin-broken",
            issue_type="Broken Road",
            location="Tonkin Highway, Redcliffe",
            severity="Urgent",
            status="Under Review",
            description="Large broken patches around a joint are forcing heavy vehicles to drift across the lane line.",
            created_at=_utc_datetime(current_year, 5, 8, 5, 35),
            reporter_id=commuter.id,
        ),
        _build_demo_report(
            key="beaufort-other",
            issue_type="Other",
            location="Beaufort Street, Mount Lawley",
            severity="Low",
            status="Reported",
            description="Raised reflective markers have come loose and are rattling under traffic throughout the evening peak.",
            created_at=_utc_datetime(current_year, 5, 11, 18, 5),
            reporter_id=resident.id,
            is_anonymous=True,
        ),
        _build_demo_report(
            key="roe-pothole",
            issue_type="Pothole",
            location="Roe Highway, Kewdale",
            severity="High",
            status="Under Review",
            description="Freight vehicles are hitting a deep pothole near the merge lane and shedding debris across the shoulder.",
            created_at=_utc_datetime(current_year, 5, 15, 5, 50),
            reporter_id=commuter.id,
            image_url="https://loremflickr.com/1200/800/highway,pothole?lock=107",
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
