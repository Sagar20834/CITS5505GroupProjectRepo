import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from .extensions import db
from .models import Comment, Confirmation, Report

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")
REPORTS_PER_PAGE = 10


def _format_address_suggestion(street_address, suburb="", postcode=""):
    street_address = " ".join((street_address or "").split())
    suburb = " ".join((suburb or "").split())
    postcode = " ".join((postcode or "").split())

    if not street_address:
        return None

    locality = " ".join(part for part in (suburb, postcode) if part)
    label = ", ".join(part for part in (street_address, locality) if part)

    return {
        "street_address": street_address,
        "suburb": suburb,
        "postcode": postcode,
        "label": label,
    }


def _local_address_suggestions(query_text):
    suggestions = (
        db.session.query(Report.street_address, Report.suburb, Report.postcode)
        .filter(Report.street_address.isnot(None))
        .filter(Report.street_address != "")
        .filter(Report.moderation_status == Report.APPROVED)
        .filter(Report.street_address.ilike(f"%{query_text}%"))
        .distinct()
        .order_by(Report.street_address.asc())
        .limit(8)
        .all()
    )

    return [
        suggestion
        for suggestion in (_format_address_suggestion(street_address, suburb, postcode) for street_address, suburb, postcode in suggestions)
        if suggestion
    ]


def _photon_address_suggestions(query_text):
    params = urlencode(
        {
            "q": f"{query_text}, Perth, Western Australia",
            "lat": -31.9505,
            "lon": 115.8605,
            "limit": 8,
            "lang": "en",
        }
    )
    request_url = f"https://photon.komoot.io/api/?{params}"
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "RoadWatchPerth/1.0 address autocomplete",
    }

    try:
        with urlopen(Request(request_url, headers=request_headers), timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError):
        return []

    features = payload.get("features", [])
    normalized = []

    for feature in features:
        properties = feature.get("properties") or {}
        if properties.get("country") and properties.get("country") != "Australia":
            continue

        street_address = properties.get("street") or properties.get("name") or ""
        suburb = (
            properties.get("district")
            or properties.get("suburb")
            or properties.get("city")
            or properties.get("locality")
            or ""
        )
        postcode = properties.get("postcode") or ""
        suggestion = _format_address_suggestion(street_address, suburb, postcode)
        if suggestion and suggestion["label"] not in {item["label"] for item in normalized}:
            normalized.append(suggestion)

    return normalized


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


def _validate_comment_body(body):
    if len(body) < 5:
        return "Comments must be at least 5 characters long."
    return None


@reports_bp.get("/")
def list_reports():
    page = max(request.args.get("page", 1, type=int), 1)
    selected_postcode = request.args.get("postcode", "").strip()
    selected_street = request.args.get("street_address", "").strip()
    selected_suburb = request.args.get("suburb", "").strip()
    selected_issue_type = request.args.get("issue_type", "").strip()
    selected_status = request.args.get("status", "").strip()
    mine_only = request.args.get("mine") == "1"

    query = Report.query

    if mine_only:
        if not current_user.is_authenticated:
            flash("Log in to filter the list to your own reports.", "warning")
            return redirect(url_for("auth.login", next=request.full_path))
        query = query.filter(Report.reporter_id == current_user.id)
    else:
        query = query.filter(Report.moderation_status == Report.APPROVED)

    if selected_postcode:
        query = query.filter(Report.postcode == selected_postcode)

    if selected_street:
        query = query.filter(Report.street_address.ilike(f"%{selected_street}%"))

    if selected_suburb:
        query = query.filter(Report.suburb.ilike(f"%{selected_suburb}%"))

    if selected_issue_type in Report.ISSUE_TYPES:
        query = query.filter(Report.issue_type == selected_issue_type)

    if selected_status in Report.STATUSES:
        query = query.filter(Report.status == selected_status)

    pagination = query.order_by(Report.created_at.desc()).paginate(page=page, per_page=REPORTS_PER_PAGE, error_out=False)

    return render_template(
        "reports.html",
        reports=pagination.items,
        pagination=pagination,
        filters={
            "postcode": selected_postcode,
            "street_address": selected_street,
            "suburb": selected_suburb,
            "issue_type": selected_issue_type,
            "status": selected_status,
            "mine": mine_only,
        },
    )


@reports_bp.get("/address-suggestions")
def address_suggestions():
    query_text = request.args.get("q", "").strip()

    if len(query_text) < 2:
        return jsonify([])

    suggestions = _photon_address_suggestions(query_text)
    if not suggestions:
        suggestions = _local_address_suggestions(query_text)

    return jsonify(suggestions)


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
            report.street_address = form_data["street_address"]
            report.suburb = form_data["suburb"]
            report.postcode = form_data["postcode"]
            report.severity = form_data["severity"]
            report.description = form_data["description"]
            report.image_url = form_data["image_url"] or None
            report.moderation_status = Report.PENDING_APPROVAL
            report.is_anonymous = form_data["is_anonymous"]
            report.reporter_id = current_user.id if current_user.is_authenticated else None
            db.session.add(report)
            db.session.commit()
            flash("Your report is waiting for admin approval.", "success")
            if current_user.is_authenticated:
                return redirect(url_for("reports.report_details", report_id=report.id))
            return redirect(url_for("reports.list_reports"))

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
    report = db.get_or_404(Report, report_id)

    if not report.can_be_viewed_by(current_user):
        flash("This report is waiting for admin approval and is not public yet.", "warning")
        return redirect(url_for("reports.list_reports"))

    comments = Comment.query.filter_by(report_id=report.id).order_by(Comment.created_at.asc()).all()
    return render_template("report_details.html", report=report, comments=comments)


@reports_bp.post("/<int:report_id>/confirm")
def toggle_confirmation(report_id):
    report = db.get_or_404(Report, report_id)

    if not report.can_be_viewed_by(current_user):
        abort(404)

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


@reports_bp.post("/<int:report_id>/comments")
def create_comment(report_id):
    report = db.get_or_404(Report, report_id)

    if not report.can_be_viewed_by(current_user):
        abort(404)

    if not current_user.is_authenticated:
        flash("Log in to join the discussion on a report.", "warning")
        return redirect(url_for("auth.login", next=url_for("reports.report_details", report_id=report.id)))

    body = request.form.get("body", "").strip()
    validation_error = _validate_comment_body(body)

    if validation_error:
        flash(validation_error, "error")
        return redirect(url_for("reports.report_details", report_id=report.id))

    comment = Comment()
    comment.body = body
    comment.report_id = report.id
    comment.author_id = current_user.id
    db.session.add(comment)
    db.session.commit()
    flash("Comment posted.", "success")
    return redirect(url_for("reports.report_details", report_id=report.id, _anchor="comments"))


@reports_bp.route("/<int:report_id>/edit", methods=["GET", "POST"])
def edit_report(report_id):
    report = db.get_or_404(Report, report_id)

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
    report = db.get_or_404(Report, report_id)

    if not report.can_be_managed_by(current_user):
        flash("Only the report owner or an admin can delete this report.", "error")
        return redirect(url_for("reports.report_details", report_id=report.id))

    db.session.delete(report)
    db.session.commit()
    flash("Report deleted.", "success")
    return redirect(url_for("reports.list_reports"))
