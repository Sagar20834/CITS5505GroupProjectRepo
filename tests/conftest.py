import re

import pytest

from roadwatch import create_app
from roadwatch.extensions import db


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    SERVER_NAME = "localhost"


@pytest.fixture()
def app():
    app = create_app(TestConfig)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner()


def extract_csrf_token(response):
    page = response.get_data(as_text=True)
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', page)
    assert match, "Expected a csrf_token hidden input in the rendered form."
    return match.group(1)
