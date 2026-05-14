# RoadWatch Perth

RoadWatch Perth is a Flask web application for reporting, reviewing, and tracking community road hazards around Perth. Users can submit road issue reports, browse approved community reports, confirm recurring issues, and discuss reports through comments. Admin users can review new reports before publication and manage progress updates.

## Purpose, Design, and Use

The purpose of RoadWatch Perth is to help local residents, commuters, and road authorities identify unsafe road conditions before they become larger problems. The application supports community reporting for issues such as potholes, cracked roads, flooding, missing signs, and other road hazards.

The application is designed around three main workflows:

- Public users can browse approved road reports, search by location, view report details, and see issue trends.
- Registered users can submit reports, track their own reports, comment on reports, and confirm that they have seen the same issue.
- Admin users can review new reports before they become public, approve or reject submissions, update repair progress, change severity, remove inappropriate content, and manage users.

Reports are stored in SQLite through SQLAlchemy models. New reports enter a pending approval state, public pages show approved reports only, and dashboard charts are generated from persisted report data. The interface is built with Flask routes, Jinja templates, Tailwind CSS, and small JavaScript enhancements such as address autocomplete and Chart.js analytics.

## Group Members


| UWA ID | Name | GitHub username |
| --- | --- | --- |
| TODO | Dipta Datta Gupta | diptadg |
| TODO | Sagar Kumar Sah Kanu | Sagar20834 |
| TODO | Harshil Patel | Harshil8802 |
| TODO | Ziqi Meng | TODO |
| TODO | Jiongge | Jiongge |

## Features

- User registration, login, logout, and account-linked reports.
- Anonymous report submission for guests and signed-in users.
- Report creation with issue type, severity, structured location, description, and optional image URL.
- No-token address autocomplete using OpenStreetMap data through Photon, with saved approved report locations as fallback.
- Admin approval workflow: pending, approved, and rejected reports.
- Public report list showing approved reports only.
- Search and filter reports by street address, suburb, postcode, issue type, and progress.
- Pagination for public reports and admin report management.
- Report confirmations so users can mark that they have seen the same issue.
- Comment threads on report detail pages.
- Admin actions for approval, progress updates, severity updates, comment deletion, report deletion, and user blocking.
- Dashboard analytics using persisted report data and Chart.js.

## Technology Stack

- Flask
- Flask-Login
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-WTF
- SQLite
- Jinja templates
- Tailwind CSS
- Chart.js
- pytest
- Selenium
- tzdata

## Project Structure

```text
app.py                  Flask app entry point
roadwatch/              Application package
templates/              Jinja templates
migrations/             Alembic/Flask-Migrate database migrations
tests/                  pytest backend workflow tests
documentation/          Project brief and user stories
```

## Launching the Application

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Apply database migrations:

```powershell
flask --app app db upgrade
```

Optionally load demo users and reports:

```powershell
flask --app app seed-demo
```

Run the app:

```powershell
flask --app app run
```

Then open `http://127.0.0.1:5000`.

## Demo Data

The demo seed command creates users, reports, comments, confirmations, status notes, structured locations, and a mix of approval states.

Default demo accounts:

```text
admin / AdminPass123
perthresident / ResidentPass123
citycommuter / CommuterPass123
perthcyclist / CyclistPass123
```

To reset local demo data:

```powershell
flask --app app reset-demo --yes
```

## Running Tests

The backend test suite uses pytest and isolated temporary SQLite databases under the ignored `instance/` directory. Tests do not modify the development database.

Run:

```powershell
python -m pytest
```

`pytest.ini` enables verbose output by default, so each test is listed with its pass/fail status.

Current coverage includes:

- User registration.
- User login and logout.
- Anonymous report submission.
- Logged-in report submission.
- Report edit and delete permissions.
- Admin-only progress and severity updates.
- Admin comment deletion.
- Model helpers such as `reporter_label`, `can_be_managed_by`, and `can_be_viewed_by`.

## Running Selenium Browser Tests

Selenium tests start the Flask app against an isolated SQLite database and drive the main workflows in a real browser. Selenium 4 uses Selenium Manager to locate or download a compatible browser driver.

Install dependencies first:

```powershell
python -m pip install -r requirements.txt
```

Run only the browser tests:

```powershell
python -m pytest -m selenium
```

By default the tests use Chrome in headless mode. You can override this with environment variables:

```powershell
$env:SELENIUM_BROWSER="edge"
$env:SELENIUM_HEADLESS="0"
python -m pytest -m selenium
```

Supported `SELENIUM_BROWSER` values are `chrome`, `edge`, and `firefox`. Selenium Manager handles browser driver discovery automatically. If Selenium cannot start the selected browser locally, the Selenium tests are skipped with a clear reason.

## Database Notes

Local SQLite database files are ignored by Git:

```text
instance/*.db
instance/*.db-journal
```

If migrations change, run:

```powershell
flask --app app db upgrade
```

To inspect the current migration head:

```powershell
flask --app app db heads
```

Timestamps are stored in UTC and displayed in Perth local time through the app's `datetime_label` template filter. The `tzdata` package is included so timezone conversion works reliably on Windows.
