import re
from uuid import uuid4

import pytest

from roadwatch import create_app
from roadwatch.config import Config
from roadwatch.extensions import db
from roadwatch.models import User


class TestConfig(Config):
    TESTING = True
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
import re
import threading

import pytest
from werkzeug.serving import make_server

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


class SeleniumTestConfig:
    TESTING = True
    SECRET_KEY = "selenium-test-secret"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True


class LiveServer:
    def __init__(self, app, server, thread):
        self.app = app
        self.server = server
        self.thread = thread
        self.url = f"http://127.0.0.1:{server.server_port}"


@pytest.fixture()
def live_server(tmp_path):
    class Config(SeleniumTestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'selenium.db'}"

    app = create_app(Config)

    with app.app_context():
        db.create_all()

    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield LiveServer(app, server, thread)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        with app.app_context():
            db.session.remove()
            db.drop_all()


@pytest.fixture()
def browser():
    selenium = pytest.importorskip("selenium")
    from selenium import webdriver
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions

    driver = None

    browser_builders = (
        (webdriver.Chrome, ChromeOptions),
        (webdriver.Edge, EdgeOptions),
    )

    for webdriver_class, options_class in browser_builders:
        options = options_class()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1280,900")

        try:
            driver = webdriver_class(options=options)
            break
        except WebDriverException:
            continue

    if driver is None:
        pytest.skip("Selenium browser driver is not available. Install Chrome or Edge and rerun the tests.")

    driver.implicitly_wait(2)
    try:
        yield driver
    finally:
        driver.quit()


def extract_csrf_token(response):
    page = response.get_data(as_text=True)
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', page)
    assert match, "Expected a csrf_token hidden input in the rendered form."
    return match.group(1)
