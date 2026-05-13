from datetime import datetime, timezone

from roadwatch.extensions import db
from roadwatch.models import Comment, Confirmation, Report, User

from conftest import extract_csrf_token


def create_user(username="resident", email="resident@example.com", password="password123", is_admin=False):
    user = User(username=username, email=email, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def create_report(
    *,
    reporter=None,
    street_address="123 Hay Street",
    moderation_status=Report.APPROVED,
    status="Reported",
    created_at=None,
):
    report = Report(
        issue_type="Pothole",
        street_address=street_address,
        suburb="Perth",
        postcode="6000",
        severity="High",
        status=status,
        moderation_status=moderation_status,
        description="Large pothole affecting the left lane near the intersection.",
        reporter=reporter,
        created_at=created_at or datetime(2026, 5, 13, 1, 30, tzinfo=timezone.utc),
        updated_at=created_at or datetime(2026, 5, 13, 1, 30, tzinfo=timezone.utc),
    )
    db.session.add(report)
    db.session.commit()
    return report


def login(client, identifier="resident", password="password123"):
    response = client.get("/login")
    token = extract_csrf_token(response)
    return client.post(
        "/login",
        data={"csrf_token": token, "identifier": identifier, "password": password},
        follow_redirects=True,
    )


def test_home_page_is_server_rendered(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"RoadWatch Perth" in response.data
    assert b"csrf_token" not in response.data


def test_user_can_register_and_login_with_flask_login(client):
    response = client.get("/register")
    token = extract_csrf_token(response)

    response = client.post(
        "/register",
        data={
            "csrf_token": token,
            "username": "newresident",
            "email": "newresident@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Account created successfully." in response.data
    assert b"newresident" in response.data
    assert User.query.filter_by(username="newresident").first() is not None


def test_post_without_csrf_token_is_rejected(client):
    response = client.post(
        "/register",
        data={
            "username": "missingtoken",
            "email": "missingtoken@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )

    assert response.status_code == 400


def test_authenticated_user_can_create_report(client):
    create_user()
    response = login(client)
    assert response.status_code == 200

    form_page = client.get("/reports/new")
    token = extract_csrf_token(form_page)

    response = client.post(
        "/reports/new",
        data={
            "csrf_token": token,
            "issue_type": "Pothole",
            "street_address": "123 Hay Street",
            "suburb": "Perth",
            "postcode": "6000",
            "severity": "High",
            "description": "Large pothole affecting the left lane near the intersection.",
            "image_url": "",
        },
        follow_redirects=True,
    )

    report = Report.query.filter_by(street_address="123 Hay Street").first()

    assert response.status_code == 200
    assert report is not None
    assert report.reporter.username == "resident"
    assert report.moderation_status == Report.PENDING_APPROVAL


def test_invalid_report_form_shows_validation_error(client):
    create_user()
    login(client)
    form_page = client.get("/reports/new")
    token = extract_csrf_token(form_page)

    response = client.post(
        "/reports/new",
        data={
            "csrf_token": token,
            "issue_type": "Pothole",
            "street_address": "Hay",
            "suburb": "P",
            "postcode": "abc",
            "severity": "High",
            "description": "Too short",
            "image_url": "",
        },
    )

    assert response.status_code == 200
    assert b"Street address should be at least 5 characters long." in response.data
    assert Report.query.count() == 0


def test_admin_page_requires_login(client):
    response = client.get("/admin/")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_non_admin_cannot_access_admin_page(client):
    create_user()
    login(client)

    response = client.get("/admin/")

    assert response.status_code == 403


def test_admin_can_approve_pending_report(client):
    admin = create_user(
        username="admin",
        email="admin@example.com",
        password="adminpass123",
        is_admin=True,
    )
    report = create_report(reporter=admin, moderation_status=Report.PENDING_APPROVAL)
    login(client, identifier="admin", password="adminpass123")
    admin_page = client.get("/admin/")
    token = extract_csrf_token(admin_page)

    response = client.post(
        f"/admin/reports/{report.id}/approval",
        data={"csrf_token": token, "moderation_status": Report.APPROVED},
        follow_redirects=True,
    )

    db.session.refresh(report)
    assert response.status_code == 200
    assert report.moderation_status == Report.APPROVED
    assert b"Report approved and published." in response.data


def test_pending_report_is_visible_to_owner_but_not_public(client):
    owner = create_user()
    report = create_report(reporter=owner, moderation_status=Report.PENDING_APPROVAL)

    public_response = client.get(f"/reports/{report.id}", follow_redirects=True)
    assert b"This report is waiting for admin approval and is not public yet." in public_response.data

    login(client)
    owner_response = client.get(f"/reports/{report.id}")

    assert owner_response.status_code == 200
    assert b"123 Hay Street" in owner_response.data


def test_logged_in_user_can_comment_and_confirm_report(client):
    user = create_user()
    report = create_report(reporter=user, moderation_status=Report.APPROVED)
    login(client)
    details_page = client.get(f"/reports/{report.id}")
    token = extract_csrf_token(details_page)

    comment_response = client.post(
        f"/reports/{report.id}/comments",
        data={"csrf_token": token, "body": "I saw this issue this morning."},
        follow_redirects=True,
    )

    details_page = client.get(f"/reports/{report.id}")
    token = extract_csrf_token(details_page)
    confirm_response = client.post(
        f"/reports/{report.id}/confirm",
        data={"csrf_token": token},
        follow_redirects=True,
    )

    assert comment_response.status_code == 200
    assert confirm_response.status_code == 200
    assert Comment.query.filter_by(report_id=report.id, author_id=user.id).count() == 1
    assert Confirmation.query.filter_by(report_id=report.id, user_id=user.id).count() == 1


def test_datetime_filter_displays_perth_time(client):
    report = create_report(created_at=datetime(2026, 5, 13, 1, 30, tzinfo=timezone.utc))

    response = client.get(f"/reports/{report.id}")

    assert response.status_code == 200
    assert b"13 May 2026, 09:30 AM" in response.data


def test_address_suggestions_endpoint_returns_json(client, monkeypatch):
    from roadwatch import reports

    monkeypatch.setattr(
        reports,
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
