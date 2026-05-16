import re
from uuid import uuid4

import pytest

from roadwatch import create_app
from roadwatch.config import Config
from roadwatch.extensions import db
from roadwatch.models import User


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key"
    WTF_CSRF_ENABLED = True


@pytest.fixture()
def app():
    database_path = Config.BASE_DIR / "instance" / f"test-{uuid4().hex}.db"

    class ConfigForTest(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{database_path.as_posix()}"

    app = create_app(ConfigForTest)

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()

    database_path.unlink(missing_ok=True)
    database_path.with_name(f"{database_path.name}-journal").unlink(missing_ok=True)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


def csrf_token(response):
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
    assert match is not None
    return match.group(1)


def make_user(username="resident", email="resident@example.com", password="Password123", *, is_admin=False):
    user = User()
    user.username = username
    user.email = email
    user.is_admin = is_admin
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def login(client, identifier="resident", password="Password123"):
    response = client.get("/login")
    token = csrf_token(response)
    return client.post(
        "/login",
        data={
            "csrf_token": token,
            "identifier": identifier,
            "password": password,
        },
        follow_redirects=False,
    )


def logout(client):
    response = client.get("/")
    token = csrf_token(response)
    return client.post("/logout", data={"csrf_token": token}, follow_redirects=False)


def report_form_data(**overrides):
    data = {
        "issue_type": "Pothole",
        "street_address": "Hay Street",
        "suburb": "Perth CBD",
        "postcode": "6000",
        "severity": "High",
        "description": "A deep pothole is affecting vehicles during peak hour.",
        "image_url": "",
    }
    data.update(overrides)
    return data
