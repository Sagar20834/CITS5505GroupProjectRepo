from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_

from .extensions import db
from .models import Confirmation, Report

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def _build_form_data(report=None):
    image_url = request.form.get("image_url")
    if image_url is None and report is not None:
        image_url = report.image_url

    return {
        "issue_type": request.form.get("issue_type", report.issue_type if report else ""),
        "location": request.form.get("location", report.location if report else ""),
        "severity": request.form.get("severity", report.severity if report else "Medium"),
        "description": request.form.get("description", report.description if report else ""),
        "image_url": (image_url or "").strip(),
        "is_anonymous": request.form.get("is_anonymous", "on" if report and report.is_anonymous else "") == "on",
    }


def _validate_report_form(form_data):
    if form_data["issue_type"] not in Report.ISSUE_TYPES:
        return "Please choose a valid issue type."
    if form_data["severity"] not in Report.SEVERITIES:
        return "Please choose a valid severity level."
    if len(form_data["location"]) < 5:
        return "Location should be at least 5 characters long."
    if len(form_data["description"]) < 15:
        return "Description should be at least 15 characters long."
    return None


@reports_bp.get("/")
def list_reports():
    search_term = request.args.get("q", "").strip()
    selected_status = request.args.get("status", "").strip()
    mine_only = request.args.get("mine") == "1"

    query = Report.query

    if search_term:
        pattern = f"%{search_term}%"
        query = query.filter(
            or_(
                Report.issue_type.ilike(pattern),
                Report.location.ilike(pattern),
                Report.description.ilike(pattern),
            )
        )

    if selected_status in Report.STATUSES:
        query = query.filter(Report.status == selected_status)

    if mine_only:
        if not current_user.is_authenticated:
            flash("Log in to filter the list to your own reports.", "warning")
            return redirect(url_for("auth.login", next=request.full_path))
        query = query.filter(Report.reporter_id == current_user.id)

    reports = query.order_by(Report.created_at.desc()).all()

    return render_template(
        "reports.html",
        reports=reports,
        filters={"q": search_term, "status": selected_status, "mine": mine_only},
    )


@reports_bp.route("/new", methods=["GET", "POST"])
def create_report():
    form_data = _build_form_data()

    if request.method == "POST":
        validation_error = _validate_report_form(form_data)

        if validation_error:
            flash(validation_error, "error")
        elif not current_user.is_authenticated and not form_data["is_anonymous"]:
            flash("Log in if you want the report linked to your account, or submit it anonymously.", "warning")
        else:
            report = Report()
            report.issue_type = form_data["issue_type"]
            report.location = form_data["location"]
            report.severity = form_data["severity"]
            report.description = form_data["description"]
            report.image_url = form_data["image_url"] or None
            report.is_anonymous = form_data["is_anonymous"]
            report.reporter_id = current_user.id if current_user.is_authenticated else None
            db.session.add(report)
            db.session.commit()
            flash("Report submitted successfully.", "success")
            return redirect(url_for("reports.report_details", report_id=report.id))

    return render_template(
        "report.html",
        form_data=form_data,
        form_action=url_for("reports.create_report"),
        page_title="Report Issue",
        heading="Report Issue",
        submit_label="Submit Report",
        editing=False,
    )


@reports_bp.route("/<int:report_id>", methods=["GET"])
def report_details(report_id):
    report = Report.query.get_or_404(report_id)
    return render_template("report_details.html", report=report)


@reports_bp.post("/<int:report_id>/confirm")
def toggle_confirmation(report_id):
    report = Report.query.get_or_404(report_id)

    if not current_user.is_authenticated:
        flash("Log in to confirm that you have seen this issue.", "warning")
        return redirect(url_for("auth.login", next=url_for("reports.report_details", report_id=report.id)))

    confirmation = Confirmation.query.filter_by(report_id=report.id, user_id=current_user.id).first()

    if confirmation:
        db.session.delete(confirmation)
        db.session.commit()
        flash("Your confirmation has been removed.", "success")
    else:
        confirmation = Confirmation()
        confirmation.report_id = report.id
        confirmation.user_id = current_user.id
        db.session.add(confirmation)
        db.session.commit()
        flash("You confirmed this report.", "success")

    return redirect(request.referrer or url_for("reports.report_details", report_id=report.id))


@reports_bp.route("/<int:report_id>/edit", methods=["GET", "POST"])
def edit_report(report_id):
    report = Report.query.get_or_404(report_id)

    if not report.can_be_managed_by(current_user):
        flash("Only the report owner or an admin can edit this report.", "error")
        return redirect(url_for("reports.report_details", report_id=report.id))

    form_data = _build_form_data(report)

    if request.method == "POST":
        validation_error = _validate_report_form(form_data)
        if validation_error:
            flash(validation_error, "error")
        else:
            report.issue_type = form_data["issue_type"]
            report.location = form_data["location"]
            report.severity = form_data["severity"]
            report.description = form_data["description"]
            report.image_url = form_data["image_url"] or None
            report.is_anonymous = form_data["is_anonymous"]
            db.session.commit()
            flash("Report updated.", "success")
            return redirect(url_for("reports.report_details", report_id=report.id))

    return render_template(
        "report.html",
        form_data=form_data,
        form_action=url_for("reports.edit_report", report_id=report.id),
        page_title="Edit Report",
        heading="Edit Report",
        submit_label="Save Changes",
        editing=True,
        report=report,
    )


@reports_bp.post("/<int:report_id>/delete")
def delete_report(report_id):
    report = Report.query.get_or_404(report_id)

    if not report.can_be_managed_by(current_user):
        flash("Only the report owner or an admin can delete this report.", "error")
        return redirect(url_for("reports.report_details", report_id=report.id))

    db.session.delete(report)
    db.session.commit()
    flash("Report deleted.", "success")
    return redirect(url_for("reports.list_reports"))
