from collections import OrderedDict
from datetime import datetime, timezone

from .extensions import db
from .models import Report

MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ISSUE_COLORS = {
    "Pothole": "#10b981",
    "Broken Road": "#ef4444",
    "Crack": "#3b82f6",
    "Flooding": "#0f766e",
    "Missing Sign": "#f59e0b",
    "Other": "#7c3aed",
}
STATUS_COLORS = {
    "Reported": "#f59e0b",
    "Under Review": "#3b82f6",
    "Fixed": "#10b981",
}


def build_issue_counts(reports):
    counts = OrderedDict((issue_type, 0) for issue_type in Report.ISSUE_TYPES)
    for report in reports:
        counts[report.issue_type] = counts.get(report.issue_type, 0) + 1
    return counts


def build_status_counts(reports):
    counts = OrderedDict((status, 0) for status in Report.STATUSES)
    for report in reports:
        counts[report.status] = counts.get(report.status, 0) + 1
    return counts


def build_monthly_issue_matrix(reports, year=None):
    selected_year = year or datetime.now(timezone.utc).year
    matrix = OrderedDict((issue_type, [0] * 12) for issue_type in Report.ISSUE_TYPES)

    for report in reports:
        if report.created_at.year != selected_year:
            continue
        month_index = report.created_at.month - 1
        matrix.setdefault(report.issue_type, [0] * 12)[month_index] += 1

    return matrix


def build_hotspots(limit=5):
    rows = (
        db.session.query(
            Report.location_key,
            db.func.min(Report.location).label("location"),
            db.func.count(Report.id).label("report_count"),
            db.func.count(db.func.distinct(Report.reporter_id)).label("reporter_count"),
        )
        .filter(
            Report.location_key.isnot(None),
            Report.location_key != "",
            Report.moderation_status == Report.APPROVED,
        )
        .group_by(Report.location_key)
        .having(db.func.count(Report.id) > 1)
        .order_by(db.desc("report_count"), db.asc("location"))
        .limit(limit)
        .all()
    )

    return [
        {
            "location": row.location,
            "report_count": row.report_count,
            "reporter_count": row.reporter_count,
        }
        for row in rows
    ]


def build_summary_cards(reports):
    status_counts = build_status_counts(reports)
    return {
        "total": len(reports),
        "reported": status_counts["Reported"],
        "under_review": status_counts["Under Review"],
        "fixed": status_counts["Fixed"],
    }


def build_breakdown_rows(counts, color_map, percentage_mode="max"):
    total = sum(counts.values())
    peak = max(counts.values()) if counts else 0
    rows = []

    for label, count in counts.items():
        if percentage_mode == "total":
            width = round((count / total) * 100, 1) if total else 0
        else:
            width = round((count / peak) * 100, 1) if peak else 0

        rows.append(
            {
                "label": label,
                "count": count,
                "width": width,
                "share": round((count / total) * 100, 1) if total else 0,
                "color": color_map[label],
            }
        )

    return rows


def build_monthly_issue_rows(matrix):
    monthly_totals = []
    for month_index in range(12):
        monthly_totals.append(sum(counts[month_index] for counts in matrix.values()))

    peak_total = max(monthly_totals) if monthly_totals else 0
    rows = []

    for month_index, month_label in enumerate(MONTH_LABELS):
        segments = []
        for issue_type, counts in matrix.items():
            count = counts[month_index]
            if count <= 0:
                continue

            segments.append(
                {
                    "label": issue_type,
                    "count": count,
                    "width": round((count / peak_total) * 100, 1) if peak_total else 0,
                    "color": ISSUE_COLORS[issue_type],
                }
            )

        rows.append(
            {
                "month": month_label,
                "total": monthly_totals[month_index],
                "segments": segments,
            }
        )

    return rows
