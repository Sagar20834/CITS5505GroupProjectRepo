# Checkpoint 3 Backend Notes

This checkpoint turns the static prototype into a Flask backend scaffold that can be extended in later stages.

## Implemented

- Flask application factory in `app.py` and `roadwatch/`
- SQLAlchemy models for `User` and `Report`
- Password hashing with Werkzeug
- Session-based authentication with Flask-Login
- Anonymous or account-linked report submission
- Searchable report listing and report detail pages
- User dashboard for personal report tracking
- Admin dashboard actions for status updates, report deletion, and blocking/unblocking users
- Aggregated analytics for issue types, statuses, and repeated locations
- Initial migration snapshot in `migrations/versions/`

## Suggested setup

1. Create a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Run `flask --app app db upgrade`.
4. Optionally run `flask --app app seed-demo`.
5. Start the server with `flask --app app run`.
