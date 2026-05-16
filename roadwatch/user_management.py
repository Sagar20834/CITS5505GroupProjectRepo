from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from .extensions import db
from .models import Comment, Confirmation, Report, User
from .security import admin_required

user_management_bp = Blueprint("user_management", __name__, url_prefix="/admin/users")
ADMIN_USERS_PER_PAGE = 8


def _build_user_activity_counts(users):
    user_ids = [user.id for user in users]
    if not user_ids:
        return {}

    report_counts = dict(
        db.session.query(Report.reporter_id, db.func.count(Report.id))
        .filter(Report.reporter_id.in_(user_ids))
        .group_by(Report.reporter_id)
        .all()
    )
    comment_counts = dict(
        db.session.query(Comment.author_id, db.func.count(Comment.id))
        .filter(Comment.author_id.in_(user_ids))
        .group_by(Comment.author_id)
        .all()
    )
    confirmation_counts = dict(
        db.session.query(Confirmation.user_id, db.func.count(Confirmation.id))
        .filter(Confirmation.user_id.in_(user_ids))
        .group_by(Confirmation.user_id)
        .all()
    )

    return {
        user_id: {
            "reports": report_counts.get(user_id, 0),
            "comments": comment_counts.get(user_id, 0),
            "confirmations": confirmation_counts.get(user_id, 0),
        }
        for user_id in user_ids
    }


@user_management_bp.get("/")
@admin_required
def user_management_panel():
    users_page = max(request.args.get("page", 1, type=int), 1)
    users_pagination = (
        User.query.order_by(User.is_admin.desc(), User.created_at.desc(), User.username.asc())
        .paginate(page=users_page, per_page=ADMIN_USERS_PER_PAGE, error_out=False)
    )
    user_summary = {
        "total": User.query.count(),
        "active": User.query.filter(User._is_active.is_(True)).count(),
        "blocked": User.query.filter(User._is_active.is_(False)).count(),
        "admins": User.query.filter(User.is_admin.is_(True)).count(),
    }

    return render_template(
        "user_management.html",
        users=users_pagination.items,
        user_activity_counts=_build_user_activity_counts(users_pagination.items),
        users_pagination=users_pagination,
        user_summary=user_summary,
    )


@user_management_bp.post("/<int:user_id>/toggle-active")
@admin_required
def toggle_user_active(user_id):
    user = db.get_or_404(User, user_id)

    if user.id == current_user.id:
        flash("You cannot disable your own admin account.", "error")
        return redirect(request.referrer or url_for("user_management.user_management_panel"))

    user.is_active = not user.is_active
    db.session.commit()

    if user.is_active:
        flash(f"{user.username} has been restored.", "success")
    else:
        flash(f"{user.username} has been blocked from logging in.", "success")

    return redirect(request.referrer or url_for("user_management.user_management_panel"))
