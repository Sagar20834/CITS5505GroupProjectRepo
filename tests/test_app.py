from roadwatch.extensions import db
from roadwatch.models import Report, User

from conftest import extract_csrf_token


def create_user(username="resident", email="resident@example.com", password="password123", is_admin=False):
    user = User(username=username, email=email, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


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
