from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import event, or_
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


def normalize_location(location):
    return " ".join((location or "").lower().split())


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    reports = db.relationship("Report", back_populates="reporter", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def find_by_identifier(identifier):
        return User.query.filter(
            or_(db.func.lower(User.username) == identifier.lower(), db.func.lower(User.email) == identifier.lower())
        ).first()

    def can_manage(self, report):
        return self.is_admin or report.reporter_id == self.id

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f"<User {self.username}>"


class Report(db.Model):
    __tablename__ = "reports"

    ISSUE_TYPES = (
        "Pothole",
        "Broken Road",
        "Crack",
        "Flooding",
        "Missing Sign",
        "Other",
    )
    STATUSES = ("Reported", "Under Review", "Fixed")
    MODERATION_STATUSES = ("Pending Approval", "Approved", "Rejected")
    PENDING_APPROVAL = "Pending Approval"
    APPROVED = "Approved"
    REJECTED = "Rejected"

    id = db.Column(db.Integer, primary_key=True)
    issue_type = db.Column(db.String(50), nullable=False, index=True)
    location = db.Column(db.String(255), nullable=False, index=True)
    location_key = db.Column(db.String(255), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="Reported", index=True)
    moderation_status = db.Column(
        db.String(30),
        nullable=False,
        default=PENDING_APPROVAL,
        index=True,
    )
    is_anonymous = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    reporter = db.relationship("User", back_populates="reports")

    @property
    def reporter_label(self):
        if self.is_anonymous:
            return "Anonymous user"
        if self.reporter:
            return self.reporter.username
        return "Guest reporter"

    def can_be_managed_by(self, user):
        return bool(user and user.is_authenticated and user.can_manage(self))

    @property
    def is_publicly_visible(self):
        return self.moderation_status == self.APPROVED

    def can_be_viewed_by(self, user):
        if self.is_publicly_visible:
            return True
        return bool(user and user.is_authenticated and (user.is_admin or self.reporter_id == user.id))

    def __repr__(self):
        return f"<Report {self.id} {self.issue_type}>"


@event.listens_for(Report, "before_insert")
@event.listens_for(Report, "before_update")
def sync_location_key(mapper, connection, target):
    target.location_key = normalize_location(target.location)
