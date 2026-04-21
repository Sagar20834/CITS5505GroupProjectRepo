from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from .extensions import db
from .models import Report, User
from .security import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("/")
@admin_required
def admin_panel():
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template("admin.html", reports=reports)


@admin_bp.post("/reports/<int:report_id>/status")
@admin_required
def update_report_status(report_id):
    report = Report.query.get_or_404(report_id)
    new_status = request.form.get("status", "").strip()

    if new_status not in Report.STATUSES:
        flash("Please select a valid report status.", "error")
        return redirect(request.referrer or url_for("admin.admin_panel"))

    report.status = new_status
    db.session.commit()
    flash("Report status updated.", "success")
    return redirect(request.referrer or url_for("admin.admin_panel"))


@admin_bp.post("/reports/<int:report_id>/delete")
@admin_required
def delete_report(report_id):
    report = Report.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    flash("Report removed from the system.", "success")
    return redirect(request.referrer or url_for("admin.admin_panel"))


@admin_bp.post("/users/<int:user_id>/toggle-active")
@admin_required
def toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot disable your own admin account.", "error")
        return redirect(request.referrer or url_for("admin.admin_panel"))

    user.is_active = not user.is_active
    db.session.commit()

    if user.is_active:
        flash(f"{user.username} has been restored.", "success")
    else:
        flash(f"{user.username} has been blocked from logging in.", "success")

    return redirect(request.referrer or url_for("admin.admin_panel"))
