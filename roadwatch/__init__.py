from datetime import datetime
from pathlib import Path

from flask import Flask, render_template
from sqlalchemy import inspect

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

SEVERITY_STYLES = {
    "Low": "bg-emerald-100 text-emerald-800",
    "Medium": "bg-sky-100 text-sky-800",
    "High": "bg-orange-100 text-orange-800",
    "Urgent": "bg-red-100 text-red-800",
}


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

    with app.app_context():
        required_tables = {"users", "reports"}
        existing_tables = set(inspect(db.engine).get_table_names())
        if not required_tables.issubset(existing_tables):
            db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.before_request
    def protect_forms():
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
