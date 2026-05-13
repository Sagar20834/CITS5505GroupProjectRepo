from conftest import csrf_token, login, logout, make_user, report_form_data

from roadwatch.extensions import db
from roadwatch.models import Comment, Report, ReportStatusNote, User


def create_report(*, reporter=None, moderation_status=Report.APPROVED):
    report = Report()
    report.issue_type = "Pothole"
    report.street_address = "Hay Street"
    report.suburb = "Perth CBD"
    report.postcode = "6000"
    report.severity = "Medium"
    report.status = "Reported"
    report.moderation_status = moderation_status
    report.description = "A pothole is causing cars to swerve near the lane marking."
    report.reporter_id = reporter.id if reporter else None
    db.session.add(report)
    db.session.commit()
    return report


def submit_report(client, **overrides):
    response = client.get("/reports/new")
    token = csrf_token(response)
    data = report_form_data(**overrides)
    data["csrf_token"] = token
    return client.post("/reports/new", data=data, follow_redirects=False)


def test_user_registration(client, app):
    response = client.get("/register")
    token = csrf_token(response)

    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "username": "newresident",
            "email": "newresident@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
        },
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)
    with app.app_context():
        user = User.query.filter_by(username="newresident").first()
        assert user is not None
        assert user.email == "newresident@example.com"
        assert user.check_password("Password123")


def test_user_login_and_logout(client, app):
    with app.app_context():
        make_user()

    response = login(client)
    assert response.status_code in (302, 303)

    with client.session_transaction() as session:
        assert session.get("_user_id") is not None

    response = logout(client)
    assert response.status_code in (302, 303)

    with client.session_transaction() as session:
        assert session.get("_user_id") is None


def test_anonymous_report_submission(client, app):
    response = submit_report(client, is_anonymous="on")
    assert response.status_code in (302, 303)

    with app.app_context():
        report = Report.query.one()
        assert report.reporter_id is None
        assert report.is_anonymous is True
        assert report.moderation_status == Report.PENDING_APPROVAL
        assert report.location == "Hay Street, Perth CBD 6000"
        assert report.location_key == "hay street, perth cbd 6000"


def test_logged_in_report_submission(client, app):
    with app.app_context():
        user = make_user()
        user_id = user.id

    login(client)
    response = submit_report(client)
    assert response.status_code in (302, 303)

    with app.app_context():
        report = Report.query.one()
        assert report.reporter_id == user_id
        assert report.is_anonymous is False
        assert report.moderation_status == Report.PENDING_APPROVAL


def test_report_edit_and_delete_permissions(client, app):
    with app.app_context():
        owner = make_user(username="owner", email="owner@example.com")
        other = make_user(username="other", email="other@example.com")
        report = create_report(reporter=owner)
        owner_id = owner.id
        report_id = report.id

    login(client, identifier="other")

    response = client.get(f"/reports/{report_id}/edit")
    assert response.status_code in (302, 303)

    response = client.get(f"/reports/{report_id}")
    token = csrf_token(response)
    response = client.post(
        f"/reports/{report_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)

    with app.app_context():
        assert db.session.get(Report, report_id) is not None

    logout(client)
    login(client, identifier="owner")

    response = client.get(f"/reports/{report_id}/edit")
    token = csrf_token(response)
    data = report_form_data(
        issue_type="Crack",
        street_address="Canning Highway",
        suburb="South Perth",
        postcode="6151",
        severity="Low",
        description="A long crack is spreading across the left lane.",
    )
    data["csrf_token"] = token
    response = client.post(f"/reports/{report_id}/edit", data=data, follow_redirects=False)
    assert response.status_code in (302, 303)

    with app.app_context():
        report = db.session.get(Report, report_id)
        assert report.issue_type == "Crack"
        assert report.reporter_id == owner_id
        assert report.moderation_status == Report.PENDING_APPROVAL

    response = client.get(f"/reports/{report_id}")
    token = csrf_token(response)
    response = client.post(
        f"/reports/{report_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)

    with app.app_context():
        assert db.session.get(Report, report_id) is None


def test_admin_status_and_severity_actions(client, app):
    with app.app_context():
        admin = make_user(username="admin", email="admin@example.com", is_admin=True)
        user = make_user()
        report = create_report(reporter=user)
        admin_id = admin.id
        report_id = report.id

    login(client)
    response = client.get("/admin/")
    assert response.status_code == 403

    logout(client)
    login(client, identifier="admin")
    admin_page = client.get("/admin/")
    token = csrf_token(admin_page)

    response = client.post(
        f"/admin/reports/{report_id}/status",
        data={
            "csrf_token": token,
            "status": "Under Review",
            "status_note": "Inspection requested after repeated community reports.",
        },
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)

    admin_page = client.get("/admin/")
    token = csrf_token(admin_page)
    response = client.post(
        f"/admin/reports/{report_id}/severity",
        data={
            "csrf_token": token,
            "severity": "Urgent",
        },
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)

    with app.app_context():
        report = db.session.get(Report, report_id)
        assert report.status == "Under Review"
        assert report.severity == "Urgent"
        note = ReportStatusNote.query.filter_by(report_id=report_id).one()
        assert note.admin_id == admin_id
        assert note.old_status == "Reported"
        assert note.new_status == "Under Review"


def test_model_helper_methods(app):
    with app.app_context():
        admin = make_user(username="admin", email="admin@example.com", is_admin=True)
        owner = make_user(username="owner", email="owner@example.com")
        other = make_user(username="other", email="other@example.com")

        owned_report = create_report(reporter=owner)
        anonymous_report = create_report(reporter=owner)
        anonymous_report.is_anonymous = True
        pending_report = create_report(reporter=owner, moderation_status=Report.PENDING_APPROVAL)
        db.session.commit()

        assert owned_report.reporter_label == "owner"
        assert anonymous_report.reporter_label == "Anonymous user"
        assert owned_report.can_be_managed_by(owner)
        assert owned_report.can_be_managed_by(admin)
        assert not owned_report.can_be_managed_by(other)
        assert owned_report.can_be_viewed_by(other)
        assert pending_report.can_be_viewed_by(owner)
        assert pending_report.can_be_viewed_by(admin)
        assert not pending_report.can_be_viewed_by(other)


def test_admin_can_delete_comments(client, app):
    with app.app_context():
        admin = make_user(username="admin", email="admin@example.com", is_admin=True)
        user = make_user()
        report = create_report(reporter=user)
        report_id = report.id
        comment = Comment()
        comment.body = "This issue is getting worse after rain."
        comment.report_id = report_id
        comment.author_id = user.id
        db.session.add(comment)
        db.session.commit()
        comment_id = comment.id

    login(client, identifier="admin")
    response = client.get(f"/reports/{report_id}")
    token = csrf_token(response)
    response = client.post(
        f"/admin/comments/{comment_id}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)

    with app.app_context():
        assert db.session.get(Comment, comment_id) is None
