# Copyright 2026 Harsha Krishne Gowda
# SPDX-License-Identifier: Apache-2.0

"""
CSV and PDF export endpoints for analytics reports.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.api_key_auth import require_api_key
from app.models.api_key import ApiKey
from app.models.event import Event
from app.models.user import User

router = APIRouter(prefix="/api/exports", tags=["exports"])

PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}


def _resolve_range(
    period: str | None,
    start_date: date | None,
    end_date: date | None,
) -> tuple[datetime, datetime]:
    """Return (start_dt, end_dt) in UTC from period string or explicit dates."""
    now = datetime.now(timezone.utc)
    if end_date is None:
        end_dt = now
    else:
        end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc)
    if start_date is not None:
        start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc)
    elif period and period in PERIOD_DAYS:
        start_dt = end_dt - timedelta(days=PERIOD_DAYS[period])
    else:
        start_dt = end_dt - timedelta(days=30)
    return start_dt, end_dt


async def _fetch_export_rows(
    db: AsyncSession,
    user_id,
    start_dt: datetime,
    end_dt: datetime,
):
    """Fetch aggregated rows grouped by date, provider, model."""
    q = (
        select(
            cast(Event.created_at, Date).label("date"),
            Event.provider,
            Event.model,
            func.count(Event.id).label("requests"),
            func.coalesce(func.sum(Event.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(Event.output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(Event.cost_usd), 0).label("cost_usd"),
        )
        .where(
            Event.user_id == user_id,
            Event.created_at >= start_dt,
            Event.created_at <= end_dt,
        )
        .group_by(cast(Event.created_at, Date), Event.provider, Event.model)
        .order_by(cast(Event.created_at, Date), Event.provider, Event.model)
    )
    result = await db.execute(q)
    return result.all()


# ── CSV export ──────────────────────────────────────────────────────────────

@router.get("/csv")
async def export_csv(
    period: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Export analytics summary as CSV."""
    _, user = auth
    start_dt, end_dt = _resolve_range(period, start_date, end_date)
    rows = await _fetch_export_rows(db, user.id, start_dt, end_dt)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "provider", "model", "requests", "input_tokens", "output_tokens", "cost_usd"])
    for r in rows:
        writer.writerow([
            str(r.date),
            r.provider,
            r.model,
            int(r.requests),
            int(r.input_tokens),
            int(r.output_tokens),
            float(r.cost_usd),
        ])

    content = buf.getvalue()
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tokenbudget_report.csv"},
    )


# ── PDF export ──────────────────────────────────────────────────────────────

@router.get("/pdf")
async def export_pdf(
    period: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    auth: tuple[ApiKey, User] = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Export analytics as PDF report."""
    _, user = auth
    start_dt, end_dt = _resolve_range(period, start_date, end_date)
    rows = await _fetch_export_rows(db, user.id, start_dt, end_dt)

    # Compute summary
    total_cost = sum(float(r.cost_usd) for r in rows)
    total_requests = sum(int(r.requests) for r in rows)
    avg_cost = total_cost / total_requests if total_requests > 0 else 0.0

    # Per-model breakdown
    model_data: dict[str, dict] = {}
    for r in rows:
        key = r.model
        if key not in model_data:
            model_data[key] = {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
        model_data[key]["requests"] += int(r.requests)
        model_data[key]["input_tokens"] += int(r.input_tokens)
        model_data[key]["output_tokens"] += int(r.output_tokens)
        model_data[key]["cost_usd"] += float(r.cost_usd)

    # Build PDF
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("TokenBudget Cost Report", styles["Title"]))
    elements.append(Spacer(1, 12))

    # Date range
    elements.append(Paragraph(
        f"Period: {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 18))

    # Summary table
    elements.append(Paragraph("Summary", styles["Heading2"]))
    summary_data = [
        ["Metric", "Value"],
        ["Total Cost (USD)", f"${total_cost:,.6f}"],
        ["Total Requests", f"{total_requests:,}"],
        ["Avg Cost / Request", f"${avg_cost:,.6f}"],
    ]
    summary_table = Table(summary_data, colWidths=[200, 200])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A90D9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 18))

    # Per-model breakdown
    elements.append(Paragraph("Per-Model Breakdown", styles["Heading2"]))
    model_table_data = [["Model", "Requests", "Input Tokens", "Output Tokens", "Cost (USD)"]]
    for model_name in sorted(model_data.keys()):
        d = model_data[model_name]
        model_table_data.append([
            model_name,
            f"{d['requests']:,}",
            f"{d['input_tokens']:,}",
            f"{d['output_tokens']:,}",
            f"${d['cost_usd']:,.6f}",
        ])

    model_table = Table(model_table_data, colWidths=[140, 80, 100, 100, 100])
    model_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A90D9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    elements.append(model_table)

    doc.build(elements)
    pdf_bytes = buf.getvalue()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=tokenbudget_report.pdf"},
    )
