import os
from threading import Thread

import pytest
from werkzeug.serving import make_server

selenium = pytest.importorskip("selenium")
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

from conftest import make_user
from roadwatch.extensions import db
from roadwatch.models import Report, User


pytestmark = pytest.mark.selenium


def create_seed_report(*, reporter=None, street_address, description, severity="Medium", status="Reported"):
    report = Report()
    report.issue_type = "Pothole"
    report.street_address = street_address
    report.suburb = "Perth CBD"
    report.postcode = "6000"
    report.severity = severity
    report.status = status
    report.moderation_status = Report.APPROVED
    report.description = description
    report.reporter_id = reporter.id if reporter else None
    db.session.add(report)
    db.session.commit()
    return report


@pytest.fixture()
def selenium_seed_data(app):
    with app.app_context():
        admin = make_user(
            username="browseradmin",
            email="browseradmin@example.com",
            password="AdminPass123",
            is_admin=True,
        )
        user = make_user(
            username="browseruser",
            email="browseruser@example.com",
            password="UserPass123",
        )
        search_report = create_seed_report(
            reporter=user,
            street_address="Selenium Search Road",
            description="Browser searchable approved report for filtering tests.",
        )
        admin_report = create_seed_report(
            reporter=user,
            street_address="Selenium Admin Road",
            description="Browser admin workflow report for progress and severity updates.",
            severity="Low",
        )

        return {
            "admin_id": admin.id,
            "user_id": user.id,
            "search_report_id": search_report.id,
            "admin_report_id": admin_report.id,
        }


@pytest.fixture()
def live_server(app, selenium_seed_data):
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield f"http://127.0.0.1:{server.server_port}"

    server.shutdown()
    thread.join(timeout=5)


def _headless_enabled():
    return os.getenv("SELENIUM_HEADLESS", "1").lower() not in {"0", "false", "no"}


def _chrome_driver():
    options = webdriver.ChromeOptions()
    if _headless_enabled():
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1200")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    return webdriver.Chrome(options=options)


def _edge_driver():
    options = webdriver.EdgeOptions()
    if _headless_enabled():
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1200")
    options.add_argument("--disable-gpu")
    return webdriver.Edge(options=options)


def _firefox_driver():
    options = webdriver.FirefoxOptions()
    if _headless_enabled():
        options.add_argument("--headless")
    options.add_argument("--width=1440")
    options.add_argument("--height=1200")
    return webdriver.Firefox(options=options)


@pytest.fixture()
def browser():
    browser_name = os.getenv("SELENIUM_BROWSER", "chrome").lower()
    driver_factories = {
        "chrome": _chrome_driver,
        "edge": _edge_driver,
        "firefox": _firefox_driver,
    }
    driver_factory = driver_factories.get(browser_name)

    if driver_factory is None:
        pytest.skip(f"Unsupported SELENIUM_BROWSER value: {browser_name}")

    try:
        driver = driver_factory()
    except WebDriverException as exc:
        pytest.skip(f"Selenium browser could not be started: {exc.msg}")

    yield driver

    driver.quit()


def wait_for_text(browser, text, timeout=10):
    WebDriverWait(browser, timeout).until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), text))


def fill_text(browser, field_id, value):
    field = browser.find_element(By.ID, field_id)
    field.clear()
    field.send_keys(value)


def login_through_browser(browser, base_url, username, password):
    browser.get(f"{base_url}/login")
    fill_text(browser, "identifier", username)
    fill_text(browser, "password", password)
    browser.find_element(By.CSS_SELECTOR, "form button[type='submit']").click()
    wait_for_text(browser, "Welcome back.")


def test_browser_user_registration(browser, live_server, app):
    browser.get(f"{live_server}/register")
    fill_text(browser, "username", "seleniumnew")
    fill_text(browser, "email", "seleniumnew@example.com")
    fill_text(browser, "password", "Password123")
    fill_text(browser, "confirm_password", "Password123")
    browser.find_element(By.CSS_SELECTOR, "form button[type='submit']").click()

    wait_for_text(browser, "Account created successfully.")

    with app.app_context():
        user = User.query.filter_by(username="seleniumnew").one()
        assert user.email == "seleniumnew@example.com"


def test_browser_navbar_opens_reports_page(browser, live_server):
    browser.get(live_server)

    browser.find_element(By.LINK_TEXT, "Reports").click()

    wait_for_text(browser, "All Reports")
    assert "/reports" in browser.current_url


def test_browser_login_and_logout(browser, live_server):
    login_through_browser(browser, live_server, "browseruser", "UserPass123")
    wait_for_text(browser, "browseruser")

    browser.find_element(By.XPATH, "//button[normalize-space()='Logout']").click()
    wait_for_text(browser, "You have been logged out.")
    wait_for_text(browser, "Login")


def test_browser_create_road_report(browser, live_server, app):
    login_through_browser(browser, live_server, "browseruser", "UserPass123")
    browser.get(f"{live_server}/reports/new")

    Select(browser.find_element(By.ID, "issue_type")).select_by_visible_text("Crack")
    fill_text(browser, "street_address", "Selenium Created Road")
    fill_text(browser, "suburb", "Perth CBD")
    fill_text(browser, "postcode", "6000")
    Select(browser.find_element(By.ID, "severity")).select_by_visible_text("High")
    fill_text(browser, "description", "Selenium-created report describing a cracked road hazard.")
    browser.find_element(By.XPATH, "//button[normalize-space()='Submit Report']").click()

    wait_for_text(browser, "Your report is waiting for admin approval.")
    wait_for_text(browser, "Report Details")

    with app.app_context():
        report = Report.query.filter_by(street_address="Selenium Created Road").one()
        assert report.moderation_status == Report.PENDING_APPROVAL
        assert report.reporter.username == "browseruser"


def test_browser_filter_reports(browser, live_server):
    browser.get(f"{live_server}/reports/")
    fill_text(browser, "street_address", "Selenium Search")
    browser.find_element(By.XPATH, "//button[normalize-space()='Apply filters']").click()

    wait_for_text(browser, "Selenium Search Road")
    assert "Browser searchable approved report" in browser.find_element(By.TAG_NAME, "body").text


def test_browser_address_suggestions_update_without_page_reload(browser, live_server, monkeypatch):
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

    browser.get(f"{live_server}/reports/new")
    original_url = browser.current_url
    browser.find_element(By.ID, "street_address").send_keys("Ha")

    WebDriverWait(browser, 5).until(
        lambda driver: driver.execute_script(
            "return document.querySelectorAll('#street-address-suggestions option').length"
        )
        > 0
    )

    option_value = browser.execute_script("return document.querySelector('#street-address-suggestions option').value")
    assert option_value == "Hay Street"
    assert browser.current_url == original_url


def test_browser_open_report_detail(browser, live_server):
    browser.get(f"{live_server}/reports/")
    report_link = WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//article[contains(., 'Selenium Search Road')]//a[normalize-space()='View']"))
    )
    report_link.click()

    wait_for_text(browser, "Report Details")
    wait_for_text(browser, "Browser searchable approved report for filtering tests.")


def test_browser_admin_status_and_severity_update(browser, live_server, app, selenium_seed_data):
    report_id = selenium_seed_data["admin_report_id"]

    login_through_browser(browser, live_server, "browseradmin", "AdminPass123")
    browser.get(f"{live_server}/admin/")

    status_select = browser.find_element(By.ID, f"status-{report_id}")
    Select(status_select).select_by_visible_text("Under Review")
    fill_text(browser, f"status-note-{report_id}", "Selenium browser status update.")
    status_select.find_element(By.XPATH, "./ancestor::form").submit()
    wait_for_text(browser, "Report progress updated.")

    severity_select = browser.find_element(By.ID, f"severity-{report_id}")
    Select(severity_select).select_by_visible_text("Urgent")
    severity_select.find_element(By.XPATH, "./ancestor::form").submit()
    wait_for_text(browser, "Report severity updated.")

    with app.app_context():
        report = db.session.get(Report, report_id)
        assert report.status == "Under Review"
        assert report.severity == "Urgent"
