Checkpoint 3 includes a Flask-Migrate / Alembic scaffold plus an initial schema revision for the `users` and `reports` tables.

Recommended workflow once dependencies are installed:

1. `flask --app app db upgrade`
2. Make model changes in `roadwatch/models.py`
3. `flask --app app db migrate -m "describe schema change"`
4. `flask --app app db upgrade`
