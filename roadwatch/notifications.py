from .extensions import db
from .models import Notification, User


def create_notification(user, message, *, report=None, link_url=""):
    if user is None:
        return None

    notification = Notification()
    notification.user = user
    notification.report = report
    notification.message = message
    notification.link_url = link_url
    db.session.add(notification)
    return notification


def create_admin_notifications(message, *, report=None, link_url=""):
    admins = User.query.filter_by(is_admin=True).all()
    for admin in admins:
        create_notification(admin, message, report=report, link_url=link_url)
