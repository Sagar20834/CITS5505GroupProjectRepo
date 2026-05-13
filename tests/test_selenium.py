from datetime import datetime, timezone

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from roadwatch.extensions import db
from roadwatch.models import Report, User


def create_user(username="resident", email="resident@example.com", password="password123", is_admin=False):
    user = User(username=username, email=email, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def create_report(street_address, moderation_status=Report.APPROVED):
    report = Report(
        issue_type="Pothole",
        street_address=street_address,
        suburb="Perth",
        postcode="6000",
        severity="High",
        status="Reported",
        moderation_status=moderation_status,
        description=f"Large pothole reported at {street_address}.",
        created_at=datetime(2026, 5, 13, 1, 30, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 13, 1, 30, tzinfo=timezone.utc),
    )
    db.session.add(report)
    db.session.commit()
    return report


def wait_for_text(browser, text):
    return WebDriverWait(browser, 5).until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), text))


def test_selenium_navbar_opens_reports_page(browser, live_server):
    browser.get(live_server.url)

    browser.find_element(By.LINK_TEXT, "Reports").click()

    wait_for_text(browser, "All Reports")
    assert "/reports" in browser.current_url


def test_selenium_user_can_register_and_is_logged_in(browser, live_server):
    browser.get(f"{live_server.url}/register")

    browser.find_element(By.ID, "username").send_keys("seleniumuser")
    browser.find_element(By.ID, "email").send_keys("selenium@example.com")
    browser.find_element(By.ID, "password").send_keys("password123")
    browser.find_element(By.ID, "confirm_password").send_keys("password123")
    browser.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    wait_for_text(browser, "Account created successfully.")
    wait_for_text(browser, "seleniumuser")


def test_selenium_reports_filter_form_shows_matching_report(browser, live_server):
    with live_server.app.app_context():
        create_report("Hay Street")
        create_report("Murray Street")

    browser.get(f"{live_server.url}/reports/")
    browser.find_element(By.ID, "street_address").send_keys("Hay")
    browser.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    wait_for_text(browser, "Hay Street")
    assert "Murray Street" not in browser.find_element(By.TAG_NAME, "body").text


def test_selenium_logged_in_user_can_submit_report(browser, live_server, monkeypatch):
    from roadwatch import reports

    monkeypatch.setattr(reports, "_photon_address_suggestions", lambda query_text: [])

    with live_server.app.app_context():
        create_user()

    browser.get(f"{live_server.url}/login")
    browser.find_element(By.ID, "identifier").send_keys("resident")
    browser.find_element(By.ID, "password").send_keys("password123")
    browser.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait_for_text(browser, "Welcome back.")

    browser.get(f"{live_server.url}/reports/new")
    Select(browser.find_element(By.ID, "issue_type")).select_by_visible_text("Pothole")
    browser.find_element(By.ID, "street_address").send_keys("456 Wellington Street")
    browser.find_element(By.ID, "suburb").send_keys("Perth")
    browser.find_element(By.ID, "postcode").send_keys("6000")
    Select(browser.find_element(By.ID, "severity")).select_by_visible_text("High")
    browser.find_element(By.ID, "description").send_keys("Large pothole blocking part of the left lane near the station.")
    browser.find_element(By.XPATH, "//form[@action='/reports/new']//button[@type='submit']").click()

    wait_for_text(browser, "Your report is waiting for admin approval.")

    with live_server.app.app_context():
        assert Report.query.filter_by(street_address="456 Wellington Street").first() is not None


def test_selenium_address_suggestions_update_without_page_reload(browser, live_server, monkeypatch):
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

    browser.get(f"{live_server.url}/reports/new")
    original_url = browser.current_url
    browser.find_element(By.ID, "street_address").send_keys("Ha")

    WebDriverWait(browser, 5).until(
        lambda driver: driver.execute_script(
            "return document.querySelectorAll('#street-address-suggestions option').length"
        )
        > 0
    )

    option_value = browser.execute_script(
        "return document.querySelector('#street-address-suggestions option').value"
    )
    assert option_value == "Hay Street"
    assert browser.current_url == original_url
