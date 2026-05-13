# RoadWatch Perth

RoadWatch Perth is a Flask web application for reporting and tracking road issues around Perth, such as potholes, cracks, flooding, broken roads, and missing signs.

The app uses server-side rendered Jinja templates, Flask-Login authentication, Flask-SQLAlchemy models, Flask-WTF CSRF protection, admin moderation, analytics dashboards, comments, confirmations, and an AJAX address suggestion endpoint.

## Features

- User registration, login, logout, and password hashing
- Anonymous or account-linked report submission
- Admin approval workflow before reports become public
- Report search/filtering by location, issue type, status, and ownership
- Report details page with comments and issue confirmations
- Admin controls for approval, status, severity, deletion, and user blocking
- Dashboard analytics for issue counts, status counts, hotspots, and monthly trends
- AJAX street address suggestions without reloading the page
- Perth timezone display for posted and updated times
- Automated tests with pytest

## Requirements

- Python 3.11 or newer
- pip
- A terminal such as PowerShell, Command Prompt, Git Bash, or macOS/Linux shell

## Setup On Windows

From the project root:

```powershell
cd D:\CITS5508GroupProjectRepo
```

Create a virtual environment:

```powershell
python -m venv venv
```

Activate it:

```powershell
.\venv\Scripts\activate
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Setup On macOS Or Linux

From the project root:

```bash
cd /path/to/CITS5508GroupProjectRepo
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Database Setup

Apply migrations:

```powershell
python -m flask --app app db upgrade
```

The app also includes a lightweight schema sync during normal app startup, but running migrations is the preferred setup process.

## Seed Demo Data

Load sample users, reports, comments, confirmations, and status notes:

```powershell
python -m flask --app app seed-demo
```

Demo accounts:

| Username | Password |
| --- | --- |
| `admin` | `AdminPass123` |
| `perthresident` | `ResidentPass123` |
| `citycommuter` | `CommuterPass123` |
| `perthcyclist` | `CyclistPass123` |

## Reset Demo Data

To clear existing local data and reload the demo dataset:

```powershell
python -m flask --app app reset-demo
python -m flask --app app seed-demo
```

To skip the reset confirmation prompt:

```powershell
python -m flask --app app reset-demo --yes
python -m flask --app app seed-demo
```

## Run The Application

Start the Flask development server:

```powershell
python -m flask --app app run
```

Open the app in your browser:

```text
http://127.0.0.1:5000
```

For debug mode:

```powershell
python -m flask --app app run --debug
```

## Run Tests

Install dependencies first, then run:

```powershell
python -m pytest
```

Current tests cover:

- Server-rendered home page
- User registration and Flask-Login session behavior
- CSRF rejection for POST requests without tokens
- Authenticated report creation using SQLAlchemy
- Report validation errors
- Admin-only access controls
- Admin report approval
- Pending report visibility rules
- Comments and issue confirmations
- Perth timezone display
- AJAX address suggestions JSON response

## Useful Commands

Check installed packages:

```powershell
python -m pip list
```

Run tests with more detail:

```powershell
python -m pytest -v
```

Create a migration after model changes:

```powershell
python -m flask --app app db migrate -m "Describe the change"
python -m flask --app app db upgrade
```

## Project Structure

```text
.
|-- app.py
|-- requirements.txt
|-- roadwatch/
|   |-- __init__.py
|   |-- admin.py
|   |-- auth.py
|   |-- cli.py
|   |-- config.py
|   |-- extensions.py
|   |-- main.py
|   |-- models.py
|   |-- reports.py
|   `-- security.py
|-- templates/
|-- migrations/
|-- documentation/
`-- tests/
```

## Security Notes

- Authentication is implemented with Flask-Login.
- Passwords are hashed with Werkzeug before being stored.
- Database access uses Flask-SQLAlchemy ORM queries.
- Forms are protected with Flask-WTF CSRF tokens.
- Jinja templates escape output by default, helping protect against XSS.

## AJAX Evidence

The report form uses JavaScript `fetch()` to call:

```text
/reports/address-suggestions?q=<partial-address>
```

The Flask route returns JSON suggestions, and the page updates the street address datalist without a full page reload.
