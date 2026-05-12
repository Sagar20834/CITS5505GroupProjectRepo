from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from .extensions import db
from .models import Comment, Report, ReportStatusNote, User
from .security import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("/")
@admin_required
def admin_panel():
    reports = Report.query.order_by(Report.created_at.desc()).all()
    pending_reports = [report for report in reports if report.moderation_status == Report.PENDING_APPROVAL]
    reviewed_reports = [report for report in reports if report.moderation_status != Report.PENDING_APPROVAL]
    return render_template("admin.html", pending_reports=pending_reports, reviewed_reports=reviewed_reports)


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

    if new_moderation_status == Report.APPROVED:
        flash("Report approved and published.", "success")
    elif new_moderation_status == Report.REJECTED:
        flash("Report rejected and removed from public view.", "success")
    else:
        flash("Report moved back to pending approval.", "success")

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
        status_note = ReportStatusNote()
        status_note.report = report
        status_note.admin_id = current_user.id
        status_note.old_status = old_status
        status_note.new_status = new_status
        status_note.note = note_text
        db.session.add(status_note)
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


@admin_bp.post("/comments/<int:comment_id>/delete")
@admin_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    report_id = comment.report_id
    db.session.delete(comment)
    db.session.commit()
    flash("Comment removed.", "success")
    return redirect(request.referrer or url_for("reports.report_details", report_id=report_id, _anchor="comments"))


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
