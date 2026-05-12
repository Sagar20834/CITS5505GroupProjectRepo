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
        "street_address": request.form.get(
            "street_address",
            (report.street_address or report.location) if report else "",
        ),
        "suburb": request.form.get("suburb", report.suburb if report else ""),
        "postcode": request.form.get("postcode", report.postcode if report else ""),
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
    if len(form_data["street_address"].strip()) < 5:
        return "Street address should be at least 5 characters long."
    if len(form_data["suburb"].strip()) < 2:
        return "Suburb should be at least 2 characters long."
    if not (form_data["postcode"].isdigit() and len(form_data["postcode"]) == 4):
        return "Postcode should be a valid 4-digit value."
    if len(form_data["description"]) < 15:
        return "Description should be at least 15 characters long."
    return None


@reports_bp.get("/")
def list_reports():
    selected_postcode = request.args.get("postcode", "").strip()
    selected_street = request.args.get("street_address", "").strip()
    selected_suburb = request.args.get("suburb", "").strip()
    selected_status = request.args.get("status", "").strip()
    mine_only = request.args.get("mine") == "1"

    query = Report.query

    if current_user.is_authenticated:
        if not current_user.is_admin:
            query = query.filter(
                or_(
                    Report.moderation_status == Report.APPROVED,
                    Report.reporter_id == current_user.id,
                )
            )
    else:
        query = query.filter(Report.moderation_status == Report.APPROVED)

    if selected_postcode:
        query = query.filter(Report.postcode.ilike(f"%{selected_postcode}%"))

    if selected_street:
        query = query.filter(Report.street_address.ilike(f"%{selected_street}%"))

    if selected_suburb:
        query = query.filter(Report.suburb.ilike(f"%{selected_suburb}%"))

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
        filters={
            "postcode": selected_postcode,
            "street_address": selected_street,
            "suburb": selected_suburb,
            "status": selected_status,
            "mine": mine_only,
        },
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
            report = Report(
                issue_type=form_data["issue_type"],
                street_address=form_data["street_address"],
                suburb=form_data["suburb"],
                postcode=form_data["postcode"],
                severity=form_data["severity"],
                description=form_data["description"],
                image_url=form_data["image_url"] or None,
                moderation_status=Report.PENDING_APPROVAL,
                is_anonymous=form_data["is_anonymous"],
                reporter_id=current_user.id if current_user.is_authenticated else None,
            )
            db.session.add(report)
            db.session.commit()
            flash("Report submitted and sent to the admin for approval.", "success")
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

    if not report.can_be_viewed_by(current_user):
        flash("This report is waiting for admin approval and is not public yet.", "warning")
        return redirect(url_for("reports.list_reports"))

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
            report.street_address = form_data["street_address"]
            report.suburb = form_data["suburb"]
            report.postcode = form_data["postcode"]
            report.severity = form_data["severity"]
            report.description = form_data["description"]
            report.image_url = form_data["image_url"] or None
            report.is_anonymous = form_data["is_anonymous"]
            if not current_user.is_admin:
                report.moderation_status = Report.PENDING_APPROVAL
            db.session.commit()
            if current_user.is_admin:
                flash("Report updated.", "success")
            else:
                flash("Report updated and sent back for admin approval.", "success")
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
