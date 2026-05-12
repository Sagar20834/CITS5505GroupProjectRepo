from datetime import datetime
from pathlib import Path
import sys

import click
from flask import Flask, render_template
from sqlalchemy import inspect
from sqlalchemy.schema import CreateIndex

from .admin import admin_bp
from .auth import auth_bp
from .cli import seed_demo_command
from .config import Config
from .extensions import db, login_manager, migrate
from .main import main_bp
from .models import Report, User
from .reports import reports_bp
from .security import generate_csrf_token, validate_csrf

STATUS_STYLES = {
    "Reported": "bg-amber-100 text-amber-800",
    "Under Review": "bg-blue-100 text-blue-800",
    "Fixed": "bg-green-100 text-green-800",
}
MODERATION_STYLES = {
    "Pending Approval": "bg-amber-100 text-amber-800",
    "Approved": "bg-green-100 text-green-800",
    "Rejected": "bg-red-100 text-red-800",
}

SEVERITY_STYLES = {
    "Low": "bg-emerald-100 text-emerald-800",
    "Medium": "bg-sky-100 text-sky-800",
    "High": "bg-orange-100 text-orange-800",
    "Urgent": "bg-red-100 text-red-800",
}


def _sql_literal(value):
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped_value = value.replace("'", "''")
        return f"'{escaped_value}'"
    return None


def _column_default_sql(column):
    if column.default is None:
        return None

    default_value = column.default.arg
    if callable(default_value):
        return None

    return _sql_literal(default_value)


def _build_add_column_sql(engine, column):
    default_sql = _column_default_sql(column)
    if not column.nullable and not column.primary_key and default_sql is None:
        raise RuntimeError(
            f"Cannot auto-add non-nullable column '{column.table.name}.{column.name}' without a scalar default."
        )

    column_sql = [
        f'ALTER TABLE "{column.table.name}" ADD COLUMN "{column.name}"',
        column.type.compile(dialect=engine.dialect),
    ]

    if default_sql is not None:
        column_sql.append(f"DEFAULT {default_sql}")
    if not column.nullable and not column.primary_key:
        column_sql.append("NOT NULL")

    return " ".join(column_sql)


def _sync_schema(engine, metadata):
    inspector = inspect(engine)
    model_table_names = set(metadata.tables.keys())
    existing_table_names = set(inspector.get_table_names())

    if not model_table_names.issubset(existing_table_names):
        metadata.create_all(bind=engine)
        inspector = inspect(engine)
        existing_table_names = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table in metadata.sorted_tables:
            if table.name not in existing_table_names:
                continue

            existing_columns = {column["name"] for column in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                connection.exec_driver_sql(_build_add_column_sql(engine, column))

            existing_indexes = {index["name"] for index in inspector.get_indexes(table.name)}
            for index in table.indexes:
                if index.name in existing_indexes:
                    continue
                connection.exec_driver_sql(str(CreateIndex(index).compile(dialect=engine.dialect)))


def _should_sync_schema():
    return "db" not in sys.argv[1:]


def create_app(config_class=Config):
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(project_root / "templates"),
    )
    app.config.from_object(config_class)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.cli.add_command(seed_demo_command)

    if _should_sync_schema():
        with app.app_context():
            _sync_schema(db.engine, db.metadata)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.extensions["seed_demo_hint_shown"] = False

    @app.before_request
    def protect_forms():
        if not app.config.get("TESTING") and not app.extensions["seed_demo_hint_shown"]:
            app.extensions["seed_demo_hint_shown"] = True
            if User.query.count() == 0 and Report.query.count() == 0:
                click.secho(
                    "Database is empty. Run `flask --app app seed-demo` to load sample users and reports.",
                    fg="yellow",
                )
        validate_csrf()

    @app.context_processor
    def inject_template_globals():
        return {
            "csrf_token": generate_csrf_token,
            "current_year": datetime.now().year,
            "issue_types": Report.ISSUE_TYPES,
            "report_statuses": Report.STATUSES,
            "report_severities": Report.SEVERITIES,
            "status_styles": STATUS_STYLES,
            "moderation_statuses": Report.MODERATION_STATUSES,
            "moderation_styles": MODERATION_STYLES,
            "severity_styles": SEVERITY_STYLES,
        }

    @app.template_filter("datetime_label")
    def datetime_label(value):
        if value is None:
            return "Unknown"
        return value.strftime("%d %b %Y, %I:%M %p")

    @app.errorhandler(400)
    def bad_request(error):
        return (
            render_template(
                "error.html",
                title="Invalid Request",
                heading="The submitted request could not be processed.",
                message="Please refresh the page and try again.",
            ),
            400,
        )

    @app.errorhandler(403)
    def forbidden(error):
        return (
            render_template(
                "error.html",
                title="Access Denied",
                heading="You do not have permission to access this page.",
                message="If you believe this is incorrect, log in with a different account or return to the reports list.",
            ),
            403,
        )

    @app.errorhandler(404)
    def not_found(error):
        return (
            render_template(
                "error.html",
                title="Page Not Found",
                heading="The page you requested does not exist.",
                message="The link may be outdated, or the report may have been removed.",
            ),
            404,
        )

    return app
