# RoadWatch Perth

RoadWatch Perth is a Flask web application for reporting, reviewing, and tracking community road hazards around Perth. Users can submit road issue reports, browse approved community reports, confirm recurring issues, and discuss reports through comments. Admin users can review new reports before publication and manage progress updates.

## Purpose, Design, and Use

The purpose of RoadWatch Perth is to help local residents, commuters, and road authorities identify unsafe road conditions before they become larger problems. The application supports community reporting for issues such as potholes, cracked roads, flooding, missing signs, and other road hazards.

The application is designed around three main workflows:

- Public users can browse approved road reports, search by location, view report details, and see issue trends.
- Registered users can submit reports, track their own reports, comment on reports, and confirm that they have seen the same issue.
- Admin users can review new reports before they become public, approve or reject submissions, update repair progress, change severity, remove inappropriate content, and manage users.

Reports are stored in SQLite through SQLAlchemy models. New reports enter a pending approval state, public pages show approved reports only, and dashboard charts are generated from persisted report data. The interface is built with Flask routes, Jinja templates, Tailwind CSS, a custom MD3-inspired Ocean Breeze theme, and JavaScript enhancements such as address autocomplete, Chart.js analytics, scroll reveal, and animated canvas/background effects.

## Group Members


| UWA ID | Name | GitHub username |
| --- | --- | --- |
| 24735786 | Dipta Datta Gupta | diptadg |
| 25143621 | Sagar Kumar Sah Kanu | Sagar20834 |
| 24585822 | Harshil Prafulbhai Ratanpara | Harshil8802 |
| 24645175 | Ziqi Meng | Jiongge |

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
- Account-dropdown notifications for report submission and moderation updates, backed by persisted database rows so unread notifications survive logout until marked read.
- Admin actions for approval, progress updates, severity updates, comment deletion, report deletion, and user blocking.
- Separate admin user management dashboard at `/admin/users/` with account status, role labels, activity counts, pagination, and block/unblock controls.
- Blocking enforcement for future logins and already-active sessions.
- Dashboard and admin hotspot panels that group approved reports by normalized location, deduplicate repeated reports from the same logged-in user, and count true guest reports as separate signals.
- Dashboard analytics using persisted report data and Chart.js.
- MD3-inspired cyberpunk visual system with Ocean Breeze color tokens, readable Space Grotesk typography, animated landing hero canvas, global ambient background, scroll reveal, card hover effects, and theme-aware chart colors.

## Technology Stack

- Flask
- Flask-Login
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-WTF
- SQLite
- Jinja templates
- Tailwind CSS
- Custom CSS and JavaScript under `roadwatch/static/`
- Chart.js
- pytest
- Selenium
- tzdata

## Project Structure

```text
app.py                  Flask app entry point
roadwatch/              Application package
roadwatch/static/       Theme stylesheet and browser-side animation/effects scripts
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

Load demo users and reports if you want data to appear in the app:

```powershell
flask --app app seed-demo
```

The application starts with an empty database. It will not contain users, reports, comments, notifications, or dashboard data until `seed-demo` is run or data is created through the web interface.

Run the app:

```powershell
flask --app app run
```

Then open `http://127.0.0.1:5000`.

### Email sharing setup

Report sharing by email sends through SMTP. This demo project includes SMTP defaults in `roadwatch/config.py` for the university presentation. To use a different sender, set environment variables before starting Flask:

```powershell
$env:MAIL_SERVER="smtp.gmail.com"
$env:MAIL_PORT="587"
$env:MAIL_USERNAME="your-email@example.com"
$env:MAIL_PASSWORD="your-app-password"
$env:MAIL_USE_TLS="true"
$env:MAIL_USE_SSL="false"
$env:MAIL_DEFAULT_SENDER="RoadWatch Perth <your-email@example.com>"
flask --app app run
```

For Gmail, use an app password rather than your normal account password. Real environment variables take precedence over the demo defaults in `roadwatch/config.py`.

## Demo Data

The demo seed command creates users, reports, comments, confirmations, status notes, structured locations, repeated-location hotspots, and a mix of approval states.

Run `flask --app app seed-demo` after setup to populate the local database. Without this step, the app is still usable, but public pages and dashboards show empty states until reports are submitted and approved.

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
- Safe `next` redirect handling during login.
- Blocked users being prevented from logging in.
- Already-logged-in users being forced out after an admin blocks them.
- Anonymous report submission.
- Logged-in report submission.
- Persisted notification creation, read-state updates, unread notification history after logout/login, and clearing read notifications from the dropdown.
- Demo reset clearing notifications along with reports, users, comments, confirmations, and status notes.
- Report edit and delete permissions.
- Pending-report visibility rules for owners, admins, and the public.
- Admin-only progress and severity updates.
- Admin user management dashboard and block/unblock behavior.
- Admin comment deletion.
- AJAX report confirmations.
- Email share success, missing-mail-configuration handling, invalid-email rejection, and WhatsApp share rendering.
- Address suggestion endpoint behavior and Photon response normalization.
- Dashboard/admin hotspot visibility and deduplication logic.
- Perth timezone display through `datetime_label`.
- Render checks for the theme stylesheet, ambient background, landing hero canvas, and animation scripts.
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

The current migration set includes the notifications table used by account-dropdown history. The application also performs a lightweight startup schema sync as a local safeguard for missing tables, columns, and indexes. Alembic migrations remain the source of truth, so `flask --app app db upgrade` should still be run after pulling schema changes.

Schema creation and migrations do not load application content. A fresh database remains empty until you run `flask --app app seed-demo` or create users and reports through the web interface.

To inspect the current migration head:

```powershell
flask --app app db heads
```

Timestamps are stored in UTC and displayed in Perth local time through the app's `datetime_label` template filter. The `tzdata` package is included so timezone conversion works reliably on Windows.
