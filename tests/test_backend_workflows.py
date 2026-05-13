from datetime import datetime, timezone

from conftest import csrf_token, login, logout, make_user, report_form_data
from roadwatch.extensions import db
from roadwatch.models import Comment, Confirmation, Report, ReportStatusNote, User


def create_report(*, reporter=None, moderation_status=Report.APPROVED, created_at=None):
    report = Report()
    report.issue_type = "Pothole"
    report.street_address = "Hay Street"
    report.suburb = "Perth CBD"
    report.postcode = "6000"
    report.severity = "Medium"
    report.status = "Reported"
    report.moderation_status = moderation_status
    report.description = "A pothole is causing cars to swerve near the lane marking."
    if created_at is not None:
        report.created_at = created_at
        report.updated_at = created_at
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


def test_home_page_is_server_rendered(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"RoadWatch Perth" in response.data


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


def test_post_without_csrf_token_is_rejected(client):
    response = client.post(
        "/register",
        data={
            "username": "missingtoken",
            "email": "missingtoken@example.com",
            "password": "Password123",
            "confirm_password": "Password123",
        },
    )

    assert response.status_code == 400


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


def test_invalid_report_form_shows_validation_error(client, app):
    with app.app_context():
        make_user()

    login(client)
    response = client.get("/reports/new")
    token = csrf_token(response)
    data = report_form_data(
        street_address="Hay",
        suburb="P",
        postcode="abc",
        description="Too short",
    )
    data["csrf_token"] = token

    response = client.post("/reports/new", data=data)

    assert response.status_code == 200
    assert b"Street address should be at least 5 characters long." in response.data
    with app.app_context():
        assert Report.query.count() == 0


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


def test_admin_can_approve_pending_report(client, app):
    with app.app_context():
        admin = make_user(username="admin", email="admin@example.com", is_admin=True)
        report = create_report(reporter=admin, moderation_status=Report.PENDING_APPROVAL)
        report_id = report.id

    login(client, identifier="admin")
    admin_page = client.get("/admin/")
    token = csrf_token(admin_page)

    response = client.post(
        f"/admin/reports/{report_id}/approval",
        data={"csrf_token": token, "moderation_status": Report.APPROVED},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Report approved and published." in response.data
    with app.app_context():
        report = db.session.get(Report, report_id)
        assert report.moderation_status == Report.APPROVED


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


def test_pending_report_is_visible_to_owner_but_not_public(client, app):
    with app.app_context():
        owner = make_user()
        report = create_report(reporter=owner, moderation_status=Report.PENDING_APPROVAL)
        report_id = report.id

    public_response = client.get(f"/reports/{report_id}", follow_redirects=True)
    assert b"This report is waiting for admin approval and is not public yet." in public_response.data

    login(client)
    owner_response = client.get(f"/reports/{report_id}")

    assert owner_response.status_code == 200
    assert b"Hay Street" in owner_response.data


def test_logged_in_user_can_comment_and_confirm_report(client, app):
    with app.app_context():
        user = make_user()
        report = create_report(reporter=user)
        user_id = user.id
        report_id = report.id

    login(client)
    details_page = client.get(f"/reports/{report_id}")
    token = csrf_token(details_page)

    comment_response = client.post(
        f"/reports/{report_id}/comments",
        data={"csrf_token": token, "body": "I saw this issue this morning."},
        follow_redirects=True,
    )

    details_page = client.get(f"/reports/{report_id}")
    token = csrf_token(details_page)
    confirm_response = client.post(
        f"/reports/{report_id}/confirm",
        data={"csrf_token": token},
        follow_redirects=True,
    )

    assert comment_response.status_code == 200
    assert confirm_response.status_code == 200
    with app.app_context():
        assert Comment.query.filter_by(report_id=report_id, author_id=user_id).count() == 1
        assert Confirmation.query.filter_by(report_id=report_id, user_id=user_id).count() == 1


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


def test_datetime_filter_displays_perth_time(client, app):
    with app.app_context():
        report = create_report(created_at=datetime(2026, 5, 13, 1, 30, tzinfo=timezone.utc))
        report_id = report.id

    response = client.get(f"/reports/{report_id}")

    assert response.status_code == 200
    assert b"13 May 2026, 09:30 AM" in response.data


def test_address_suggestions_endpoint_returns_json(client, monkeypatch):
    import roadwatch.reports as reports_module

    monkeypatch.setattr(
        reports_module,
        "_photon_address_suggestions",
        lambda query_text: [
            {
                "street_address": "Hay Street",
                "suburb": "Perth",
                "postcode": "6000",
                "label": "Hay Street, Perth 6000",
            }
        ],
    )

    response = client.get(
        "/reports/address-suggestions?q=ha",
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    assert response.is_json
    assert response.get_json()[0]["street_address"] == "Hay Street"
