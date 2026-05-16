import io
import json
from datetime import datetime, timezone

from conftest import csrf_token, login, logout, make_user, report_form_data
from roadwatch.analytics import build_hotspots
from roadwatch.extensions import db
from roadwatch.models import Comment, Confirmation, Notification, Report, ReportStatusNote, User


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
    assert b"theme.css" in response.data
    assert b"rw-ambient-bg" in response.data
    assert b'id="hero-canvas"' in response.data
    assert b"hero-canvas.js" in response.data
    assert b"site-effects.js" in response.data


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


def test_login_next_redirect_only_allows_local_paths(client, app):
    with app.app_context():
        make_user()

    response = login(client, identifier="resident")
    assert response.status_code in (302, 303)
    assert response.headers["Location"].endswith("/dashboard")

    logout(client)
    response = client.get("/login?next=/reports")
    token = csrf_token(response)
    response = client.post(
        "/login?next=/reports",
        data={
            "csrf_token": token,
            "identifier": "resident",
            "password": "Password123",
            "next": "/reports",
        },
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)
    assert response.headers["Location"].endswith("/reports")

    unsafe_targets = [
        "//evil.example/login",
        "////evil.example/login",
        "javascript:alert(1)",
        "reports",
    ]
    for unsafe_target in unsafe_targets:
        logout(client)
        response = client.get(f"/login?next={unsafe_target}")
        token = csrf_token(response)
        response = client.post(
            "/login",
            data={
                "csrf_token": token,
                "identifier": "resident",
                "password": "Password123",
                "next": unsafe_target,
            },
            follow_redirects=False,
        )

        assert response.status_code in (302, 303)
        assert response.headers["Location"].endswith("/dashboard")


def test_blocked_user_cannot_login(client, app):
    with app.app_context():
        user = make_user()
        user.is_active = False
        db.session.commit()

    response = login(client)

    assert response.status_code == 200
    assert b"This account has been blocked. Contact an administrator." in response.data
    with client.session_transaction() as session:
        assert session.get("_user_id") is None


def test_logged_in_user_is_forced_out_when_blocked(client, app):
    with app.app_context():
        user = make_user()
        user_id = user.id

    login(client)
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user is not None
        user.is_active = False
        db.session.commit()

    response = client.get("/profile", follow_redirects=True)

    assert response.status_code == 200
    assert b"This account has been blocked. Contact an administrator." in response.data
    assert b"Login" in response.data
    with client.session_transaction() as session:
        assert session.get("_user_id") is None


def test_user_profile_and_password_change(client, app):
    with app.app_context():
        make_user()

    login(client)
    profile_response = client.get("/profile")
    assert profile_response.status_code == 200
    assert b"resident@example.com" in profile_response.data
    assert b"User Management" not in profile_response.data

    password_page = client.get("/change-password")
    token = csrf_token(password_page)
    response = client.post(
        "/change-password",
        data={
            "csrf_token": token,
            "current_password": "Password123",
            "new_password": "NewPassword123",
            "confirm_password": "NewPassword123",
        },
        follow_redirects=False,
    )

    assert response.status_code in (302, 303)
    with app.app_context():
        user = User.query.filter_by(username="resident").one()
        assert user.check_password("NewPassword123")


def test_profile_shows_user_management_link_only_to_admins(client, app):
    with app.app_context():
        make_user()
        make_user(username="admin", email="admin@example.com", is_admin=True)

    login(client)
    resident_profile = client.get("/profile")
    assert resident_profile.status_code == 200
    assert b"User Management" not in resident_profile.data

    logout(client)
    login(client, identifier="admin")
    admin_profile = client.get("/profile")
    assert admin_profile.status_code == 200
    assert b"User Management" in admin_profile.data
    assert b"/admin/users/" in admin_profile.data


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


def test_report_notifications_are_created_and_marked_read(client, app):
    with app.app_context():
        make_user(username="admin", email="admin@example.com", is_admin=True)
        user = make_user()
        user_id = user.id

    login(client)
    response = submit_report(client)
    assert response.status_code in (302, 303)

    with app.app_context():
        report = Report.query.one()
        report_id = report.id
        admin = User.query.filter_by(username="admin").one()
        user_notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()
        admin_notifications = Notification.query.filter_by(user_id=admin.id, is_read=False).all()
        assert any("waiting for admin approval" in notification.message for notification in user_notifications)
        assert any("New report awaiting approval" in notification.message for notification in admin_notifications)

    logout(client)
    login(client, identifier="admin")
    admin_page = client.get("/admin/")
    assert b"rw-chip-warning" in admin_page.data
    assert b"dark:text-gray-500" not in admin_page.data
    token = csrf_token(admin_page)
    response = client.post(
        f"/admin/reports/{report_id}/approval",
        data={"csrf_token": token, "moderation_status": Report.APPROVED},
        follow_redirects=False,
    )
    assert response.status_code in (302, 303)

    with app.app_context():
        approved_notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()
        assert any("approved and published" in notification.message for notification in approved_notifications)

    logout(client)
    login(client)
    profile_page = client.get("/profile")
    token = csrf_token(profile_page)
    response = client.post(
        "/notifications/read",
        data={"csrf_token": token},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )
    assert response.status_code == 200
    assert response.is_json
    payload = response.get_json()
    assert payload is not None
    assert payload["ok"] is True

    with app.app_context():
        assert Notification.query.filter_by(user_id=user_id, is_read=False).count() == 0

    logout(client)
    login(client)
    history_page = client.get("/")
    assert b"Your report is waiting for admin approval." not in history_page.data
    assert b"Your report has been approved and published." not in history_page.data
    assert b"No notifications yet." in history_page.data


def test_reset_demo_clears_notification_history(runner, app):
    with app.app_context():
        user = make_user()
        report = create_report(reporter=user)
        notification = Notification()
        notification.user_id = user.id
        notification.report_id = report.id
        notification.message = "Temporary notification before reset."
        db.session.add(notification)
        db.session.commit()

        assert Notification.query.count() == 1

    result = runner.invoke(args=["reset-demo", "--yes"])

    assert result.exit_code == 0
    assert "Local app data was reset and fresh demo data was loaded." in result.output
    with app.app_context():
        assert Notification.query.count() == 0
        assert User.query.filter_by(username="admin").first() is not None


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
        assert report is not None
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
        assert report is not None
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
        assert report is not None
        assert report.status == "Under Review"
        assert report.severity == "Urgent"
        note = ReportStatusNote.query.filter_by(report_id=report_id).one()
        assert note.admin_id == admin_id
        assert note.old_status == "Reported"
        assert note.new_status == "Under Review"


def test_user_management_page_shows_users_dashboard_and_can_block_user(client, app):
    with app.app_context():
        make_user(username="admin", email="admin@example.com", is_admin=True)
        user = make_user()
        report = create_report(reporter=user)
        comment = Comment()
        comment.body = "This issue is getting worse after rain."
        comment.report_id = report.id
        comment.author_id = user.id
        confirmation = Confirmation()
        confirmation.report_id = report.id
        confirmation.user_id = user.id
        db.session.add_all([comment, confirmation])
        db.session.commit()
        user_id = user.id

    login(client, identifier="admin")
    users_page = client.get("/admin/users/")

    assert users_page.status_code == 200
    assert b"Admin Users Dashboard" in users_page.data
    assert b"resident@example.com" in users_page.data
    assert b"1 reports / 1 comments / 1 confirmations" in users_page.data

    token = csrf_token(users_page)
    response = client.post(
        f"/admin/users/{user_id}/toggle-active",
        data={"csrf_token": token},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"resident has been blocked from logging in." in response.data
    assert b"Blocked" in response.data
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user is not None
        assert user.is_active is False

    users_page = client.get("/admin/users/")
    token = csrf_token(users_page)
    response = client.post(
        f"/admin/users/{user_id}/toggle-active",
        data={"csrf_token": token},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"resident has been restored." in response.data
    with app.app_context():
        user = db.session.get(User, user_id)
        assert user is not None
        assert user.is_active is True


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


def test_ajax_confirm_returns_json_and_does_not_redirect(client, app):
    with app.app_context():
        user = make_user()
        report = create_report(reporter=user)
        report_id = report.id
        user_id = user.id

    login(client)
    details_page = client.get(f"/reports/{report_id}")
    token = csrf_token(details_page)

    response = client.post(
        f"/reports/{report_id}/confirm",
        data={"csrf_token": token},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    assert response.is_json
    payload = response.get_json()
    assert payload is not None
    assert payload["ok"] is True
    assert payload["confirmed"] is True
    assert payload["count"] == 1
    assert "confirmed" in payload["message"].lower()

    with app.app_context():
        assert Confirmation.query.filter_by(report_id=report_id, user_id=user_id).count() == 1

    response = client.post(
        f"/reports/{report_id}/confirm",
        data={"csrf_token": token},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload is not None
    assert payload["ok"] is True
    assert payload["confirmed"] is False
    assert payload["count"] == 0
    assert "removed" in payload["message"].lower()

    with app.app_context():
        assert Confirmation.query.filter_by(report_id=report_id, user_id=user_id).count() == 0


def test_report_can_be_shared_by_email(client, app, monkeypatch):
    with app.app_context():
        report = create_report()
        report_id = report.id

    sent = {}

    def fake_send(report, recipient_email):
        sent["report_id"] = report.id
        sent["recipient_email"] = recipient_email

    monkeypatch.setattr("roadwatch.reports._send_report_share_email", fake_send)
    reports_page = client.get("/reports/")
    token = csrf_token(reports_page)

    response = client.post(
        f"/reports/{report_id}/share/email",
        data={"csrf_token": token, "email": "neighbour@example.com"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 200
    assert response.is_json
    payload = response.get_json()
    assert payload is not None
    assert payload["ok"] is True
    assert sent == {"report_id": report_id, "recipient_email": "neighbour@example.com"}


def test_reports_page_renders_whatsapp_share_controls(client, app):
    with app.app_context():
        report = create_report()
        report_id = report.id

    response = client.get("/reports/")

    assert response.status_code == 200
    assert b"Share by WhatsApp" in response.data
    assert b'id="share-whatsapp"' in response.data
    assert b"https://wa.me/?text=" in response.data
    assert b"encodeURIComponent(text)" in response.data
    assert b'data-report-title="Pothole"' in response.data
    assert b'data-report-location="Hay Street, Perth CBD 6000"' in response.data
    assert f'data-email-url="/reports/{report_id}/share/email"'.encode() in response.data


def test_report_email_share_requires_mail_configuration(client, app):
    with app.app_context():
        report = create_report()
        report_id = report.id
        app.config["MAIL_SERVER"] = ""

    reports_page = client.get("/reports/")
    token = csrf_token(reports_page)

    response = client.post(
        f"/reports/{report_id}/share/email",
        data={"csrf_token": token, "email": "neighbour@example.com"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 503
    assert response.is_json
    payload = response.get_json()
    assert payload is not None
    assert payload["ok"] is False
    assert "not configured" in payload["message"]


def test_report_email_share_rejects_invalid_email(client, app, monkeypatch):
    with app.app_context():
        report = create_report()
        report_id = report.id

    def fake_send(report, recipient_email):
        raise AssertionError("Invalid email should not be sent")

    monkeypatch.setattr("roadwatch.reports._send_report_share_email", fake_send)
    reports_page = client.get("/reports/")
    token = csrf_token(reports_page)

    response = client.post(
        f"/reports/{report_id}/share/email",
        data={"csrf_token": token, "email": "not-an-email"},
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert response.status_code == 400
    assert response.is_json
    payload = response.get_json()
    assert payload is not None
    assert payload["ok"] is False


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


def test_hotspots_deduplicate_linked_user_reports_and_count_guests(app):
    with app.app_context():
        first_user = make_user(username="first", email="first@example.com")
        second_user = make_user(username="second", email="second@example.com")

        create_report(reporter=first_user)
        create_report(reporter=first_user)
        assert build_hotspots() == []

        create_report(reporter=second_user)
        create_report()
        create_report()

        hotspots = build_hotspots(limit=5)

    assert len(hotspots) == 1
    assert hotspots[0]["location"] == "Hay Street, Perth CBD 6000"
    assert hotspots[0]["report_count"] == 4
    assert hotspots[0]["reporter_count"] == 2
    assert hotspots[0]["guest_count"] == 2


def test_hotspots_are_visible_on_dashboard_and_admin_pages(client, app):
    with app.app_context():
        admin = make_user(username="admin", email="admin@example.com", is_admin=True)
        user = make_user()
        admin_username = admin.username
        create_report(reporter=user)
        create_report()

    dashboard_response = client.get("/dashboard")

    assert dashboard_response.status_code == 200
    assert b"Repeated Locations" in dashboard_response.data
    assert b"Hay Street, Perth CBD 6000" in dashboard_response.data
    assert b"1 linked reporter" in dashboard_response.data
    assert b"+ 1 guest report" in dashboard_response.data
    assert b"2 unique signals" in dashboard_response.data

    login(client, identifier=admin_username, password="Password123")
    admin_response = client.get("/admin/")

    assert admin_response.status_code == 200
    assert b"Repeated Locations" in admin_response.data
    assert b"Hay Street, Perth CBD 6000" in admin_response.data
    assert b"1 linked reporter" in admin_response.data
    assert b"+ 1 guest report" in admin_response.data
    assert b"2 unique signals" in admin_response.data


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
    payload = response.get_json()
    assert payload is not None
    assert payload[0]["street_address"] == "Hay Street"


def test_photon_address_suggestions_normalize_address_fields(app, monkeypatch):
    import roadwatch.reports as reports_module

    class FakeResponse:
        def __enter__(self):
            payload = {
                "features": [
                    {
                        "properties": {
                            "country": "Australia",
                            "housenumber": "12",
                            "street": "Hay Street",
                            "suburb": "Perth",
                            "postcode": 6000,
                        }
                    }
                ]
            }
            return io.BytesIO(json.dumps(payload).encode("utf-8"))

        def __exit__(self, exc_type, exc, traceback):
            return False

    monkeypatch.setattr(reports_module, "urlopen", lambda request, timeout: FakeResponse())

    with app.app_context():
        suggestions = reports_module._photon_address_suggestions("hay")

    assert suggestions == [
        {
            "street_address": "12 Hay Street",
            "suburb": "Perth",
            "postcode": "6000",
            "label": "12 Hay Street, Perth 6000",
        }
    ]
