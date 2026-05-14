from datetime import datetime, timezone
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

import click
from flask import Flask, redirect, render_template, url_for
from flask_login import current_user
from flask_wtf.csrf import CSRFError, generate_csrf
from sqlalchemy import inspect
from sqlalchemy.schema import CreateIndex

from .admin import admin_bp
from .auth import auth_bp
from .cli import reset_demo_command, seed_demo_command
from .config import Config
from .extensions import csrf, db, login_manager, migrate
from .main import main_bp
from .models import Notification, Report, User
from .reports import reports_bp

STATUS_STYLES = {
    "Reported": "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100",
    "Under Review": "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100",
    "Fixed": "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
}
MODERATION_STYLES = {
    "Pending Approval": "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-100",
    "Approved": "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
    "Rejected": "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100",
}

SEVERITY_STYLES = {
    "Low": "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-100",
    "Medium": "bg-sky-100 text-sky-800 dark:bg-sky-900 dark:text-sky-100",
    "High": "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100",
    "Urgent": "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100",
}
LOCAL_TIMEZONE = ZoneInfo("Australia/Perth")


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


def _should_show_seed_demo_hint():
    cli_args = sys.argv[1:]
    if not cli_args:
        return True
    return "run" in cli_args


def create_app(config_class=Config):
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(project_root / "templates"),
    )
    app.config.from_object(config_class)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    csrf.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.cli.add_command(seed_demo_command)
    app.cli.add_command(reset_demo_command)

    if _should_sync_schema():
        with app.app_context():
            _sync_schema(db.engine, db.metadata)
            if not app.config.get("TESTING") and _should_show_seed_demo_hint():
                if User.query.count() == 0 and Report.query.count() == 0:
                    click.secho(
                        "Database is empty. Run `flask --app app seed-demo` to load sample users and reports.",
                        fg="yellow",
                    )

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.route("/favicon.ico")
    def favicon():
        return redirect(url_for("static", filename="favicon.svg"))

    @app.context_processor
    def inject_template_globals():
        unread_notifications = []
        unread_notification_count = 0
        if current_user.is_authenticated:
            unread_notification_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            unread_notifications = (
                Notification.query.filter_by(user_id=current_user.id)
                .order_by(Notification.created_at.desc())
                .limit(5)
                .all()
            )

        return {
            "csrf_token": generate_csrf,
            "current_year": datetime.now(LOCAL_TIMEZONE).year,
            "issue_types": Report.ISSUE_TYPES,
            "report_statuses": Report.STATUSES,
            "report_severities": Report.SEVERITIES,
            "status_styles": STATUS_STYLES,
            "moderation_statuses": Report.MODERATION_STATUSES,
            "moderation_styles": MODERATION_STYLES,
            "severity_styles": SEVERITY_STYLES,
            "unread_notification_count": unread_notification_count,
            "recent_notifications": unread_notifications,
        }

    @app.template_filter("datetime_label")
    def datetime_label(value):
        if value is None:
            return "Unknown"
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(LOCAL_TIMEZONE).strftime("%d %b %Y, %I:%M %p")

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        return (
            render_template(
                "error.html",
                title="Invalid Request",
                heading="The submitted request could not be processed.",
                message="Please refresh the page and try again.",
            ),
            400,
        )

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
