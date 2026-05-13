from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import case

from .extensions import db
from .models import Report, ReportStatusNote, User
from .security import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("/")
@admin_required
def admin_panel():
    scope = request.args.get("scope", "").strip().lower()
    selected_scope = scope if scope in {"pending", "approved", "rejected", "all"} else "pending"

    query = Report.query
    if selected_scope == "pending":
        query = query.filter(Report.moderation_status == Report.PENDING_APPROVAL)
    elif selected_scope == "approved":
        query = query.filter(Report.moderation_status == Report.APPROVED)
    elif selected_scope == "rejected":
        query = query.filter(Report.moderation_status == Report.REJECTED)

    reports = query.order_by(
        case(
            (Report.moderation_status == Report.PENDING_APPROVAL, 0),
            (Report.moderation_status == Report.REJECTED, 1),
            else_=2,
        ),
        Report.created_at.desc(),
    ).all()

    report_counts = {
        "total": Report.query.count(),
        "pending": Report.query.filter(Report.moderation_status == Report.PENDING_APPROVAL).count(),
        "approved": Report.query.filter(Report.moderation_status == Report.APPROVED).count(),
        "rejected": Report.query.filter(Report.moderation_status == Report.REJECTED).count(),
    }

    return render_template(
        "admin.html",
        reports=reports,
        selected_scope=selected_scope,
        report_counts=report_counts,
    )


@admin_bp.post("/reports/<int:report_id>/approval")
@admin_required
def update_report_approval(report_id):
    report = Report.query.get_or_404(report_id)
    new_moderation_status = request.form.get("moderation_status", "").strip()

    if new_moderation_status not in Report.MODERATION_STATUSES:
        flash("Please select a valid approval status.", "error")
        return redirect(request.referrer or url_for("admin.admin_panel"))

    report.moderation_status = new_moderation_status
    db.session.commit()
    flash("Report approval status updated.", "success")
    return redirect(request.referrer or url_for("admin.admin_panel"))


@admin_bp.post("/reports/<int:report_id>/status")
@admin_required
def update_report_status(report_id):
    report = Report.query.get_or_404(report_id)
    new_status = request.form.get("status", "").strip()
    note_text = request.form.get("status_note", "").strip()

    if new_status not in Report.STATUSES:
        flash("Please select a valid report status.", "error")
        return redirect(request.referrer or url_for("admin.admin_panel"))
    if note_text and len(note_text) > 500:
        flash("Status notes must be 500 characters or fewer.", "error")
        return redirect(request.referrer or url_for("admin.admin_panel"))

    old_status = report.status
    report.status = new_status
    if note_text:
        db.session.add(
            ReportStatusNote(
                report=report,
                admin_id=current_user.id,
                old_status=old_status,
                new_status=new_status,
                note=note_text,
            )
        )
    db.session.commit()
    flash("Report status updated.", "success")
    return redirect(request.referrer or url_for("admin.admin_panel"))


@admin_bp.post("/reports/<int:report_id>/severity")
@admin_required
def update_report_severity(report_id):
    report = Report.query.get_or_404(report_id)
    new_severity = request.form.get("severity", "").strip()

    if new_severity not in Report.SEVERITIES:
        flash("Please select a valid severity level.", "error")
        return redirect(request.referrer or url_for("admin.admin_panel"))

    report.severity = new_severity
    db.session.commit()
    flash("Report severity updated.", "success")
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
