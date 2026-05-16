from flask import Blueprint, render_template

from .analytics import (
    build_hotspots,
    build_issue_counts,
    build_monthly_issue_matrix,
    build_status_counts,
    build_summary_cards,
)
from .models import Report

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():
    reports = (
        Report.query.filter(Report.moderation_status == Report.APPROVED)
        .order_by(Report.created_at.desc())
        .all()
    )
    issue_counts = build_issue_counts(reports)
    monthly_issue_matrix = build_monthly_issue_matrix(reports)
    chart_data = {
        "labels": list(monthly_issue_matrix.keys()),
        "monthLabels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "datasets": list(monthly_issue_matrix.values()),
    }

    return render_template(
        "index.html",
        recent_reports=reports[:5],
        hotspots=build_hotspots(limit=4),
        summary=build_summary_cards(reports),
        issue_counts=issue_counts,
        chart_data=chart_data,
    )


@main_bp.get("/dashboard")
def dashboard():
    reports = (
        Report.query.filter(Report.moderation_status == Report.APPROVED)
        .order_by(Report.created_at.desc())
        .all()
    )
    issue_counts = build_issue_counts(reports)
    status_counts = build_status_counts(reports)
    chart_data = {
        "issueLabels": list(issue_counts.keys()),
        "issueValues": list(issue_counts.values()),
        "statusLabels": list(status_counts.keys()),
        "statusValues": list(status_counts.values()),
    }

    return render_template(
        "dashboard.html",
        summary=build_summary_cards(reports),
        hotspots=build_hotspots(limit=6),
        chart_data=chart_data,
    )
