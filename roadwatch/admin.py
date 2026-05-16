from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from .analytics import build_hotspots
from .extensions import db
from .models import Comment, Report, ReportStatusNote
from .notifications import create_notification
from .security import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
ADMIN_REPORTS_PER_PAGE = 5


@admin_bp.get("/")
@admin_required
def admin_panel():
    pending_page = max(request.args.get("pending_page", 1, type=int), 1)
    reviewed_page = max(request.args.get("reviewed_page", 1, type=int), 1)

    pending_pagination = (
        Report.query.filter(Report.moderation_status == Report.PENDING_APPROVAL)
        .order_by(Report.created_at.desc())
        .paginate(page=pending_page, per_page=ADMIN_REPORTS_PER_PAGE, error_out=False)
    )
    reviewed_pagination = (
        Report.query.filter(Report.moderation_status != Report.PENDING_APPROVAL)
        .order_by(Report.created_at.desc())
        .paginate(page=reviewed_page, per_page=ADMIN_REPORTS_PER_PAGE, error_out=False)
    )

    return render_template(
        "admin.html",
        pending_reports=pending_pagination.items,
        reviewed_reports=reviewed_pagination.items,
        hotspots=build_hotspots(limit=6),
        pending_pagination=pending_pagination,
        reviewed_pagination=reviewed_pagination,
    )


@admin_bp.post("/reports/<int:report_id>/approval")
@admin_required
def update_report_approval(report_id):
    report = db.get_or_404(Report, report_id)
    new_moderation_status = request.form.get("moderation_status", "").strip()
    old_moderation_status = report.moderation_status

    if new_moderation_status not in Report.MODERATION_STATUSES:
        flash("Please select a valid approval status.", "error")
        return redirect(request.referrer or url_for("admin.admin_panel"))

    report.moderation_status = new_moderation_status
    if report.reporter and old_moderation_status != new_moderation_status:
        if new_moderation_status == Report.APPROVED:
            message = "Your report has been approved and published."
        elif new_moderation_status == Report.REJECTED:
            message = "Your report was rejected and removed from public view."
        else:
            message = "Your report is waiting for admin approval."
        create_notification(
            report.reporter,
            message,
            report=report,
            link_url=url_for("reports.report_details", report_id=report.id),
        )
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
    report = db.get_or_404(Report, report_id)
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
    flash("Report progress updated.", "success")
    return redirect(request.referrer or url_for("admin.admin_panel"))


@admin_bp.post("/reports/<int:report_id>/severity")
@admin_required
def update_report_severity(report_id):
    report = db.get_or_404(Report, report_id)
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
    report = db.get_or_404(Report, report_id)
    db.session.delete(report)
    db.session.commit()
    flash("Report removed from the system.", "success")
    return redirect(request.referrer or url_for("admin.admin_panel"))


@admin_bp.post("/comments/<int:comment_id>/delete")
@admin_required
def delete_comment(comment_id):
    comment = db.get_or_404(Comment, comment_id)
    report_id = comment.report_id
    db.session.delete(comment)
    db.session.commit()
    flash("Comment removed.", "success")
    return redirect(request.referrer or url_for("reports.report_details", report_id=report_id, _anchor="comments"))

