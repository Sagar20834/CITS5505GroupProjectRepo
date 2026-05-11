from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from .extensions import db
from .models import User

auth_bp = Blueprint("auth", __name__)


def _safe_redirect_target(default_endpoint="main.dashboard"):
    candidate = request.args.get("next") or request.form.get("next")
    if candidate and not urlsplit(candidate).netloc:
        return candidate
    return url_for(default_endpoint)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form_data = {
        "username": request.form.get("username", "").strip(),
        "email": request.form.get("email", "").strip().lower(),
    }

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not form_data["username"] or not form_data["email"] or not password:
            flash("Username, email, and password are required.", "error")
        elif len(form_data["username"]) < 3:
            flash("Username must be at least 3 characters long.", "error")
        elif len(password) < 8:
            flash("Password must be at least 8 characters long.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        elif User.query.filter_by(username=form_data["username"]).first():
            flash("That username is already in use.", "error")
        elif User.query.filter_by(email=form_data["email"]).first():
            flash("That email address is already registered.", "error")
        else:
            user = User()
            user.username = form_data["username"]
            user.email = form_data["email"]
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Account created successfully.", "success")
            return redirect(url_for("main.dashboard"))

    return render_template("register.html", form_data=form_data)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    identifier = request.form.get("identifier", "").strip()

    if request.method == "POST":
        password = request.form.get("password", "")
        user = User.find_by_identifier(identifier)

        if user is None or not user.check_password(password):
            flash("Invalid username/email or password.", "error")
        elif not user.is_active:
            flash("This account has been blocked. Contact an administrator.", "error")
        else:
            login_user(user)
            flash("Welcome back.", "success")
            return redirect(_safe_redirect_target())

    return render_template("login.html", identifier=identifier)


@auth_bp.post("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.index"))
