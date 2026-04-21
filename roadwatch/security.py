from functools import wraps
from secrets import token_hex

from flask import abort, request, session
from flask_login import current_user, login_required


def generate_csrf_token():
    token = session.get("_csrf_token")
    if token is None:
        token = token_hex(16)
        session["_csrf_token"] = token
    return token


def validate_csrf():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return

    submitted_token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not submitted_token or submitted_token != session.get("_csrf_token"):
        abort(400)


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped_view(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped_view
