from datetime import datetime, timezone

from sqlalchemy import UniqueConstraint, event, or_
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


def normalize_location(location):
    return " ".join((location or "").lower().split())


def clean_location_part(value):
    return " ".join((value or "").split())


def compose_location(street_address, suburb, postcode):
    street_address = clean_location_part(street_address)
    suburb = clean_location_part(suburb)
    postcode = clean_location_part(postcode)

    locality = " ".join(part for part in (suburb, postcode) if part)
    return ", ".join(part for part in (street_address, locality) if part)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    _is_active = db.Column("is_active", db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    reports = db.relationship("Report", back_populates="reporter", lazy="dynamic")
    comments = db.relationship(
        "Comment",
        back_populates="author",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    confirmations = db.relationship(
        "Confirmation",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    notifications = db.relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

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

    @property
    def is_active(self):
        return bool(self._is_active)

    @is_active.setter
    def is_active(self, value):
        self._is_active = bool(value)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

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
    SEVERITIES = ("Low", "Medium", "High", "Urgent")

    id = db.Column(db.Integer, primary_key=True)
    issue_type = db.Column(db.String(50), nullable=False, index=True)
    location = db.Column(db.String(255), nullable=False, index=True)
    location_key = db.Column(db.String(255), nullable=False, index=True)
    street_address = db.Column(db.String(255), nullable=False, default="", index=True)
    suburb = db.Column(db.String(120), nullable=False, default="", index=True)
    postcode = db.Column(db.String(10), nullable=False, default="", index=True)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="Reported", index=True)
    moderation_status = db.Column(
        db.String(30),
        nullable=False,
        default=PENDING_APPROVAL,
        index=True,
    )
    severity = db.Column(db.String(20), nullable=False, default="Medium", index=True)
    is_anonymous = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    reporter = db.relationship("User", back_populates="reports")
    status_notes = db.relationship(
        "ReportStatusNote",
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="ReportStatusNote.created_at.desc()",
    )
    comments = db.relationship(
        "Comment",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="Comment.created_at.asc()",
    )
    confirmations = db.relationship(
        "Confirmation",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    notifications = db.relationship(
        "Notification",
        back_populates="report",
        cascade="all, delete-orphan",
    )

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

    @property
    def confirmation_count(self):
        return db.session.query(db.func.count(Confirmation.id)).filter_by(report_id=self.id).scalar() or 0

    def is_confirmed_by(self, user):
        if not user or not user.is_authenticated:
            return False
        return (
            db.session.query(Confirmation.id)
            .filter_by(report_id=self.id, user_id=user.id)
            .first()
            is not None
        )

    def __repr__(self):
        return f"<Report {self.id} {self.issue_type}>"


class ReportStatusNote(db.Model):
    __tablename__ = "report_status_notes"

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    old_status = db.Column(db.String(30), nullable=False)
    new_status = db.Column(db.String(30), nullable=False)
    note = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    report = db.relationship("Report", back_populates="status_notes")
    admin = db.relationship("User")

    @property
    def admin_label(self):
        return self.admin.username if self.admin else "Admin"

    def __repr__(self):
        return f"<ReportStatusNote {self.id} report={self.report_id}>"


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    report = db.relationship("Report", back_populates="comments")
    author = db.relationship("User", back_populates="comments")

    def __repr__(self):
        return f"<Comment {self.id} report={self.report_id} author={self.author_id}>"


class Confirmation(db.Model):
    __tablename__ = "confirmations"
    __table_args__ = (UniqueConstraint("user_id", "report_id", name="uq_confirmations_user_report"),)

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)

    user = db.relationship("User", back_populates="confirmations")
    report = db.relationship("Report", back_populates="confirmations")

    def __repr__(self):
        return f"<Confirmation user={self.user_id} report={self.report_id}>"


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = db.Column(db.Integer, db.ForeignKey("reports.id", ondelete="CASCADE"), nullable=True, index=True)
    message = db.Column(db.String(255), nullable=False)
    link_url = db.Column(db.String(500), nullable=False, default="")
    is_read = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    user = db.relationship("User", back_populates="notifications")
    report = db.relationship("Report", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.id} user={self.user_id} read={self.is_read}>"


@event.listens_for(Report, "before_insert")
@event.listens_for(Report, "before_update")
def sync_location_key(mapper, connection, target):
    target.street_address = clean_location_part(target.street_address)
    target.suburb = clean_location_part(target.suburb)
    target.postcode = clean_location_part(target.postcode)
    target.location = compose_location(target.street_address, target.suburb, target.postcode) or clean_location_part(target.location)
    target.location_key = normalize_location(target.location)
