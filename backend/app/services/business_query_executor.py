"""
Business Query Executor for the Pothys AGM AI Executive Assistant.

This module handles ALL business data queries by:
  1. Mapping intents to ORM-based PostgreSQL queries
  2. Returning structured Python dicts (not formatted strings)
  3. Formatting the final response via LLM (with deterministic fallback)

Business data NEVER touches the RAG pipeline.
"""

import re
import json
import logging
from typing import Optional, Any, List
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.branch import Branch
from app.models.report import DailyReport
from app.models.employee import Employee
from app.models.employee_performance import EmployeePerformance
from app.models.meeting import Meeting
from app.models.task import Task
from app.models.user import User
from app.services.intent_classifier import (
    BusinessIntent, extract_branch_name, extract_date_context
)
from app.core.config import settings

logger = logging.getLogger(__name__)


def _short_name(full_name: str) -> str:
    """Strip 'Swarna Mahal' from branch names for display."""
    return full_name.replace("Swarna Mahal", "").strip()


def _fmt_currency(val: Any) -> str:
    """Format a numeric value as Indian Rupee currency."""
    if val is None:
        return "Rs. 0"
    try:
        v = float(val)
        if v < 100000:
            return f"Rs. {v:,.0f}"
        elif v < 10000000:
            return f"Rs. {v/100000:.2f}L"
        else:
            return f"Rs. {v/10000000:.2f}Cr"
    except (ValueError, TypeError):
        return f"Rs. {val}"


# ─────────────────────────────────────────────
# Query Functions — each returns structured data
# ─────────────────────────────────────────────

async def _query_report_status(db: AsyncSession, query_date: date) -> dict:
    """Fetch submitted vs pending report status for all branches."""
    branches_res = await db.execute(select(Branch))
    all_branches = branches_res.scalars().all()

    reports_res = await db.execute(
        select(DailyReport).where(DailyReport.date == query_date)
    )
    reports = reports_res.scalars().all()
    report_map = {r.branch_id: r for r in reports}

    submitted = []
    pending = []
    for b in all_branches:
        name = _short_name(b.name)
        if b.id in report_map:
            r = report_map[b.id]
            time_str = (
                r.uploaded_at.strftime("%I:%M %p") if r.uploaded_at else
                r.created_at.strftime("%I:%M %p") if r.created_at else "N/A"
            )
            submitted.append({
                "branch": name,
                "revenue": float(r.total_revenue or r.sales_amount or 0),
                "status": r.status or "SUBMITTED",
                "time": time_str
            })
        else:
            pending.append(name)

    return {
        "query_type": "REPORT_STATUS",
        "date": str(query_date),
        "total_branches": len(all_branches),
        "submitted_count": len(submitted),
        "pending_count": len(pending),
        "submitted": submitted,
        "pending": pending,
    }


async def _find_branch_by_name(db: AsyncSession, search_str: str) -> Optional[Branch]:
    """Find branch using robust case, dot, space, and substring matching."""
    if not search_str:
        return None
    branches_res = await db.execute(select(Branch))
    all_branches = branches_res.scalars().all()
    clean_search = re.sub(r'[^\w]', '', search_str.lower())

    for b in all_branches:
        clean_name = re.sub(r'[^\w]', '', b.name.lower())
        clean_code = re.sub(r'[^\w]', '', (b.code or "").lower())
        if clean_search == clean_name or clean_search in clean_name or clean_name in clean_search or clean_search == clean_code:
            return b

    return None


async def _query_branch_report(db: AsyncSession, branch_name: str, query_date: date) -> dict:
    """Fetch the full daily report for a specific branch."""
    branch = await _find_branch_by_name(db, branch_name)
    if not branch:
        return {"query_type": "BRANCH_REPORT", "error": f"Branch '{branch_name}' not found."}

    report_res = await db.execute(
        select(DailyReport).where(
            and_(DailyReport.branch_id == branch.id, DailyReport.date == query_date)
        )
    )
    report = report_res.scalars().first()
    if not report:
        return {
            "query_type": "BRANCH_REPORT",
            "branch": _short_name(branch.name),
            "date": str(query_date),
            "status": "NOT_SUBMITTED",
            "message": f"No report has been submitted for {_short_name(branch.name)} on {query_date}."
        }

    return {
        "query_type": "BRANCH_REPORT",
        "branch": _short_name(branch.name),
        "date": str(query_date),
        "status": report.status or "SUBMITTED",
        "total_revenue": float(report.total_revenue or report.sales_amount or 0),
        "gold_sales": float(report.gold_sales or 0),
        "silver_sales": float(report.silver_sales or 0),
        "platinum_sales": float(report.platinum_sales or 0),
        "diamond_sales": float(report.diamond_sales or 0),
        "digigold_enrollments": report.digigold_enrollments or 0,
        "digisilver_enrollments": report.digisilver_enrollments or 0,
        "employees_present": report.employees_present or report.attendance_count or 0,
        "employees_absent": report.employees_absent or 0,
        "customer_complaints": report.customer_complaints or "None",
        "operational_issues": report.operational_issues or report.issues or "None",
        "manager_remarks": report.remarks or "None",
    }


async def _query_pending_reports(db: AsyncSession, query_date: date) -> dict:
    """Fetch branches that have NOT submitted today's report."""
    branches_res = await db.execute(select(Branch))
    all_branches = branches_res.scalars().all()

    reports_res = await db.execute(
        select(DailyReport).where(DailyReport.date == query_date)
    )
    submitted_ids = {r.branch_id for r in reports_res.scalars().all()}

    pending = [_short_name(b.name) for b in all_branches if b.id not in submitted_ids]
    submitted = [_short_name(b.name) for b in all_branches if b.id in submitted_ids]

    return {
        "query_type": "PENDING_REPORTS",
        "date": str(query_date),
        "total_branches": len(all_branches),
        "pending_count": len(pending),
        "submitted_count": len(submitted),
        "pending": pending,
        "submitted": submitted,
    }


async def _query_submitted_reports(db: AsyncSession, query_date: date) -> dict:
    """Fetch branches that HAVE submitted today's report."""
    branches_res = await db.execute(select(Branch))
    all_branches = branches_res.scalars().all()
    branch_map = {b.id: b for b in all_branches}

    reports_res = await db.execute(
        select(DailyReport).where(DailyReport.date == query_date)
    )
    submitted_reports = reports_res.scalars().all()

    submitted = []
    for r in submitted_reports:
        b = branch_map.get(r.branch_id)
        if b:
            time_str = (
                r.uploaded_at.strftime("%I:%M %p") if r.uploaded_at else
                r.created_at.strftime("%I:%M %p") if r.created_at else "N/A"
            )
            submitted.append({
                "branch": _short_name(b.name),
                "revenue": float(r.total_revenue or r.sales_amount or 0),
                "time": time_str
            })

    return {
        "query_type": "SUBMITTED_REPORTS",
        "date": str(query_date),
        "submitted_count": len(submitted),
        "submitted": submitted,
    }


async def _query_top_branch(db: AsyncSession, query_date: date) -> dict:
    """Fetch the branch with the highest revenue today along with full branch rankings."""
    branches_res = await db.execute(select(Branch))
    branch_map = {b.id: b for b in branches_res.scalars().all()}

    reports_res = await db.execute(
        select(DailyReport).where(DailyReport.date == query_date)
    )
    reports = reports_res.scalars().all()
    if not reports:
        return {
            "query_type": "TOP_BRANCH",
            "date": str(query_date),
            "message": "No reports submitted yet. Revenue data is unavailable."
        }

    top = max(reports, key=lambda r: float(r.total_revenue or r.sales_amount or 0))
    branch = branch_map.get(top.branch_id)

    rankings = []
    for r in sorted(reports, key=lambda x: float(x.total_revenue or x.sales_amount or 0), reverse=True):
        b = branch_map.get(r.branch_id)
        if b:
            rankings.append({
                "branch": _short_name(b.name),
                "revenue": float(r.total_revenue or r.sales_amount or 0)
            })

    return {
        "query_type": "TOP_BRANCH",
        "date": str(query_date),
        "branch": _short_name(branch.name) if branch else "Unknown",
        "total_revenue": float(top.total_revenue or top.sales_amount or 0),
        "gold_sales": float(top.gold_sales or 0),
        "silver_sales": float(top.silver_sales or 0),
        "platinum_sales": float(top.platinum_sales or 0),
        "diamond_sales": float(top.diamond_sales or 0),
        "rankings": rankings,
    }


async def _query_top_performer(db: AsyncSession, query_date: date, branch_name: Optional[str] = None) -> dict:
    """Fetch the highest performing employee today across branches."""
    stmt = (
        select(EmployeePerformance, Employee, Branch)
        .join(Employee, EmployeePerformance.employee_id == Employee.id)
        .join(DailyReport, EmployeePerformance.report_id == DailyReport.id)
        .join(Branch, Employee.branch_id == Branch.id)
        .where(DailyReport.date == query_date)
    )

    if branch_name:
        stmt = stmt.where(Branch.name.ilike(f"%{branch_name}%"))

    stmt = stmt.order_by(
        (func.coalesce(EmployeePerformance.gold, 0) + func.coalesce(EmployeePerformance.silver, 0) +
         func.coalesce(EmployeePerformance.platinum, 0) + func.coalesce(EmployeePerformance.diamond, 0)).desc()
    )

    res = await db.execute(stmt)
    rows = res.all()

    if not rows:
        return {
            "query_type": "TOP_PERFORMER",
            "date": str(query_date),
            "message": "No employee performance data available for today."
        }

    perf, emp, branch = rows[0]
    total = float((perf.gold or 0) + (perf.silver or 0) + (perf.platinum or 0) + (perf.diamond or 0))

    all_performers = []
    for p, e, b in rows:
        tot = float((p.gold or 0) + (p.silver or 0) + (p.platinum or 0) + (p.diamond or 0))
        all_performers.append({
            "employee_name": e.name,
            "branch": _short_name(b.name),
            "designation": e.designation,
            "total_sales": tot,
        })

    return {
        "query_type": "TOP_PERFORMER",
        "date": str(query_date),
        "employee_name": emp.name,
        "branch": _short_name(branch.name),
        "designation": emp.designation,
        "total_sales": total,
        "gold": float(perf.gold or 0),
        "silver": float(perf.silver or 0),
        "platinum": float(perf.platinum or 0),
        "diamond": float(perf.diamond or 0),
        "digigold": perf.digigold or 0,
        "all_performers": all_performers,
    }


async def _query_today_revenue(db: AsyncSession, query_date: date) -> dict:
    """Fetch total revenue and product-line aggregations across all reporting branches."""
    branches_res = await db.execute(select(Branch))
    branch_map = {b.id: b for b in branches_res.scalars().all()}

    reports_res = await db.execute(
        select(DailyReport).where(DailyReport.date == query_date)
    )
    reports = reports_res.scalars().all()
    if not reports:
        return {
            "query_type": "TODAY_REVENUE",
            "date": str(query_date),
            "message": "No reports submitted yet. Revenue data is unavailable."
        }

    total = sum(float(r.total_revenue or r.sales_amount or 0) for r in reports)
    gold = sum(float(r.gold_sales or 0) for r in reports)
    silver = sum(float(r.silver_sales or 0) for r in reports)
    platinum = sum(float(r.platinum_sales or 0) for r in reports)
    diamond = sum(float(r.diamond_sales or 0) for r in reports)

    breakdown = []
    for r in reports:
        b = branch_map.get(r.branch_id)
        breakdown.append({
            "branch": _short_name(b.name) if b else "Unknown",
            "revenue": float(r.total_revenue or r.sales_amount or 0),
            "target_achievement": float(r.target_achievement or 0),
        })

    return {
        "query_type": "TODAY_REVENUE",
        "date": str(query_date),
        "total_revenue": total,
        "gold_sales": gold,
        "silver_sales": silver,
        "platinum_sales": platinum,
        "diamond_sales": diamond,
        "branch_count": len(reports),
        "breakdown": sorted(breakdown, key=lambda x: x["revenue"], reverse=True),
    }


async def _query_attendance(db: AsyncSession, query_date: date) -> dict:
    """Fetch staff attendance and absentees aggregations across all reporting branches."""
    branches_res = await db.execute(select(Branch))
    branch_map = {b.id: b for b in branches_res.scalars().all()}

    reports_res = await db.execute(
        select(DailyReport).where(DailyReport.date == query_date)
    )
    reports = reports_res.scalars().all()
    if not reports:
        return {
            "query_type": "ATTENDANCE",
            "date": str(query_date),
            "message": "No reports submitted yet. Attendance data is unavailable."
        }

    total_present = sum(int(r.employees_present or r.attendance_count or 0) for r in reports)
    total_absent = sum(int(r.employees_absent or 0) for r in reports)
    breakdown = []
    for r in reports:
        b = branch_map.get(r.branch_id)
        breakdown.append({
            "branch": _short_name(b.name) if b else "Unknown",
            "present": int(r.employees_present or r.attendance_count or 0),
            "absent": int(r.employees_absent or 0),
        })

    return {
        "query_type": "ATTENDANCE",
        "date": str(query_date),
        "total_present": total_present,
        "total_absent": total_absent,
        "branch_count": len(reports),
        "breakdown": sorted(breakdown, key=lambda x: x["present"], reverse=True),
    }


async def _query_complaints(db: AsyncSession, query_date: date) -> dict:
    """Fetch customer complaints aggregations from today's reports."""
    branches_res = await db.execute(select(Branch))
    branch_map = {b.id: b for b in branches_res.scalars().all()}

    reports_res = await db.execute(
        select(DailyReport).where(DailyReport.date == query_date)
    )
    reports = reports_res.scalars().all()

    complaints = []
    for r in reports:
        if r.customer_complaints and r.customer_complaints.strip().lower() != "none" and r.customer_complaints.strip():
            b = branch_map.get(r.branch_id)
            complaints.append({
                "branch": _short_name(b.name) if b else "Unknown",
                "complaint": r.customer_complaints.strip(),
            })

    return {
        "query_type": "COMPLAINTS",
        "date": str(query_date),
        "count": len(complaints),
        "complaints": complaints,
    }


async def _query_alerts(db: AsyncSession, query_date: date) -> dict:
    """Fetch operational alerts/issues from today's reports."""
    branches_res = await db.execute(select(Branch))
    branch_map = {b.id: b for b in branches_res.scalars().all()}

    reports_res = await db.execute(
        select(DailyReport).where(DailyReport.date == query_date)
    )
    reports = reports_res.scalars().all()

    alerts = []
    for r in reports:
        issue_text = r.operational_issues or r.issues
        if issue_text and issue_text.strip().lower() != "none" and issue_text.strip():
            b = branch_map.get(r.branch_id)
            alerts.append({
                "branch": _short_name(b.name) if b else "Unknown",
                "issue": issue_text.strip(),
            })

    return {
        "query_type": "ALERTS",
        "date": str(query_date),
        "count": len(alerts),
        "alerts": alerts,
    }


async def _query_remarks(db: AsyncSession, query_date: date) -> dict:
    """Fetch manager remarks from today's reports."""
    branches_res = await db.execute(select(Branch))
    branch_map = {b.id: b for b in branches_res.scalars().all()}

    reports_res = await db.execute(
        select(DailyReport).where(DailyReport.date == query_date)
    )
    reports = reports_res.scalars().all()

    remarks = []
    for r in reports:
        if r.remarks and r.remarks.strip():
            b = branch_map.get(r.branch_id)
            remarks.append({
                "branch": _short_name(b.name) if b else "Unknown",
                "remark": r.remarks.strip(),
            })

    return {
        "query_type": "REMARKS",
        "date": str(query_date),
        "count": len(remarks),
        "remarks": remarks,
    }


async def _query_gold_sales(db: AsyncSession, query_date: date) -> dict:
    """Fetch gold sales breakdown."""
    branches_res = await db.execute(select(Branch))
    branch_map = {b.id: b for b in branches_res.scalars().all()}

    reports_res = await db.execute(
        select(DailyReport).where(DailyReport.date == query_date)
    )
    reports = reports_res.scalars().all()
    if not reports:
        return {"query_type": "GOLD_SALES", "date": str(query_date), "message": "No reports submitted yet."}

    total_gold = sum(float(r.gold_sales or 0) for r in reports)
    top = max(reports, key=lambda r: float(r.gold_sales or 0))
    b = branch_map.get(top.branch_id)

    breakdown = []
    for r in sorted(reports, key=lambda x: float(x.gold_sales or 0), reverse=True):
        br = branch_map.get(r.branch_id)
        if br:
            breakdown.append({
                "branch": _short_name(br.name),
                "gold_sales": float(r.gold_sales or 0)
            })

    return {
        "query_type": "GOLD_SALES",
        "date": str(query_date),
        "total_gold_sales": total_gold,
        "top_branch": _short_name(b.name) if b else "Unknown",
        "top_gold_sales": float(top.gold_sales or 0),
        "breakdown": breakdown,
    }


async def _query_diamond_sales(db: AsyncSession, query_date: date) -> dict:
    """Fetch top diamond sales performer."""
    stmt = (
        select(EmployeePerformance, Employee, Branch)
        .join(Employee, EmployeePerformance.employee_id == Employee.id)
        .join(DailyReport, EmployeePerformance.report_id == DailyReport.id)
        .join(Branch, Employee.branch_id == Branch.id)
        .where(DailyReport.date == query_date)
        .order_by(EmployeePerformance.diamond.desc())
    )
    res = await db.execute(stmt)
    rows = res.all()
    if not rows or float(rows[0][0].diamond or 0) == 0:
        return {"query_type": "DIAMOND_SALES", "date": str(query_date), "message": "No diamond sales recorded."}

    perf, emp, branch = rows[0]
    return {
        "query_type": "DIAMOND_SALES",
        "date": str(query_date),
        "employee": emp.name,
        "branch": _short_name(branch.name),
        "diamond_amount": float(perf.diamond),
    }


async def _query_digigold(db: AsyncSession, query_date: date) -> dict:
    """Fetch DigiGold/DigiSilver enrollment data."""
    stmt = (
        select(EmployeePerformance, Employee, Branch)
        .join(Employee, EmployeePerformance.employee_id == Employee.id)
        .join(DailyReport, EmployeePerformance.report_id == DailyReport.id)
        .join(Branch, Employee.branch_id == Branch.id)
        .where(DailyReport.date == query_date)
        .order_by(EmployeePerformance.digigold.desc())
    )
    res = await db.execute(stmt)
    rows = res.all()
    if not rows or (rows[0][0].digigold or 0) == 0:
        return {"query_type": "DIGIGOLD", "date": str(query_date), "message": "No DigiGold enrollments recorded."}

    perf, emp, branch = rows[0]
    return {
        "query_type": "DIGIGOLD",
        "date": str(query_date),
        "employee": emp.name,
        "branch": _short_name(branch.name),
        "digigold_enrollments": perf.digigold,
        "digisilver_enrollments": perf.digisilver or 0,
    }


async def _query_agenda(db: AsyncSession, user_id: Optional[Any] = None, query_date: Optional[date] = None) -> dict:
    """Fetch today's executive agenda summary."""
    if query_date is None:
        query_date = date.today()
    branches_res = await db.execute(select(Branch))
    all_branches = branches_res.scalars().all()

    reports_res = await db.execute(
        select(DailyReport).where(DailyReport.date == query_date)
    )
    reports = reports_res.scalars().all()

    start_of_day = datetime.combine(query_date, datetime.min.time())
    end_of_day = datetime.combine(query_date, datetime.max.time())
    meetings_res = await db.execute(
        select(Meeting).where(and_(Meeting.start_time >= start_of_day, Meeting.start_time <= end_of_day))
    )
    meetings = meetings_res.scalars().all()

    tasks_res = await db.execute(
        select(Task).where(and_(Task.due_date == query_date, Task.status != "COMPLETED"))
    )
    tasks = tasks_res.scalars().all()

    submitted_count = len(reports)
    alerts_count = len([r for r in reports if (r.issues or r.operational_issues) and (r.issues or r.operational_issues).strip()])

    return {
        "query_type": "AGENDA",
        "date": str(query_date),
        "meetings_count": len(meetings),
        "meetings": [{"title": m.title, "time": m.start_time.strftime("%I:%M %p"), "status": m.status} for m in meetings],
        "tasks_count": len(tasks),
        "tasks": [{"title": t.title, "priority": t.priority, "status": t.status} for t in tasks],
        "submitted_reports": submitted_count,
        "pending_reports": len(all_branches) - submitted_count,
        "alerts_count": alerts_count,
    }


async def _query_meetings(db: AsyncSession, user_id: Optional[Any] = None) -> dict:
    """Fetch all scheduled meetings."""
    meetings_res = await db.execute(select(Meeting).order_by(Meeting.start_time.asc()))
    meetings = meetings_res.scalars().all()

    return {
        "query_type": "MEETINGS",
        "count": len(meetings),
        "meetings": [
            {
                "title": m.title,
                "date": m.start_time.strftime("%d-%b-%Y"),
                "time": m.start_time.strftime("%I:%M %p"),
                "agenda": m.agenda or "No agenda specified",
                "status": m.status,
            }
            for m in meetings
        ],
    }


async def _query_tasks(db: AsyncSession, user_id: Optional[Any] = None) -> dict:
    """Fetch all tasks."""
    tasks_res = await db.execute(select(Task).order_by(Task.due_date.asc()))
    tasks = tasks_res.scalars().all()

    return {
        "query_type": "TASKS",
        "count": len(tasks),
        "tasks": [
            {
                "title": t.title,
                "due_date": t.due_date.strftime("%d-%b-%Y"),
                "priority": t.priority,
                "status": t.status,
                "description": t.description or "None",
            }
            for t in tasks
        ],
    }


async def _query_comparison(db: AsyncSession, query: str, query_date: date) -> dict:
    """Compare performance of two or more branches."""
    branches_res = await db.execute(select(Branch))
    all_branches = branches_res.scalars().all()

    q_lower = query.lower()
    matched = [b for b in all_branches if b.name.split(' ')[0].lower() in q_lower or b.code.lower() in q_lower]
    if len(matched) < 2:
        matched = all_branches

    reports_res = await db.execute(
        select(DailyReport).where(DailyReport.date == query_date)
    )
    reports = reports_res.scalars().all()
    report_map = {r.branch_id: r for r in reports}

    comparison = []
    for b in matched:
        r = report_map.get(b.id)
        entry = {"branch": _short_name(b.name), "status": "NOT_SUBMITTED"}
        if r:
            entry.update({
                "status": "SUBMITTED",
                "total_revenue": float(r.total_revenue or r.sales_amount or 0),
                "gold_sales": float(r.gold_sales or 0),
                "silver_sales": float(r.silver_sales or 0),
                "platinum_sales": float(r.platinum_sales or 0),
                "diamond_sales": float(r.diamond_sales or 0),
                "attendance": int(r.employees_present or r.attendance_count or 0),
                "absent": int(r.employees_absent or 0),
                "target_achievement": float(r.target_achievement or 0),
                "operational_issues": r.operational_issues or r.issues or "None",
                "remarks": r.remarks or "None",
            })
        comparison.append(entry)

    return {
        "query_type": "COMPARISON",
        "date": str(query_date),
        "branches": comparison
    }


async def _query_branch_metric(db: AsyncSession, branch_name: str, metric: str, query_date: date) -> dict:
    """Fetch ONLY a specific metric for a specific branch."""
    branch = await _find_branch_by_name(db, branch_name)
    if not branch:
        return {
            "query_type": "BRANCH_METRIC",
            "branch": branch_name,
            "metric": metric,
            "date": str(query_date),
            "status": "NOT_FOUND",
            "message": f"Branch '{branch_name}' not found."
        }

    report_res = await db.execute(
        select(DailyReport).where(
            and_(DailyReport.branch_id == branch.id, DailyReport.date == query_date)
        )
    )
    report = report_res.scalars().first()
    b_name = _short_name(branch.name)

    if not report:
        return {
            "query_type": "BRANCH_METRIC",
            "branch": b_name,
            "metric": metric,
            "date": str(query_date),
            "status": "NOT_SUBMITTED",
            "message": f"No report submitted for {b_name} on {query_date}."
        }

    # Extract ONLY requested metric
    metric_data = {}
    if metric == "attendance":
        metric_data = {
            "present": report.employees_present or report.attendance_count or 0,
            "absent": report.employees_absent or 0,
        }
    elif metric == "gold_sales":
        metric_data = {"gold_sales": float(report.gold_sales or 0)}
    elif metric == "silver_sales":
        metric_data = {"silver_sales": float(report.silver_sales or 0)}
    elif metric == "platinum_sales":
        metric_data = {"platinum_sales": float(report.platinum_sales or 0)}
    elif metric == "diamond_sales":
        metric_data = {"diamond_sales": float(report.diamond_sales or 0)}
    elif metric == "total_revenue":
        metric_data = {"total_revenue": float(report.total_revenue or report.sales_amount or 0)}
    elif metric == "complaints":
        metric_data = {"customer_complaints": report.customer_complaints or "None reported"}
    elif metric == "issues":
        metric_data = {"operational_issues": report.issues or report.operational_issues or "None reported"}
    elif metric == "remarks":
        metric_data = {"manager_remarks": report.remarks or report.manager_remarks or "None recorded"}
    elif metric == "digigold":
        metric_data = {
            "digigold_enrollments": report.digigold_enrollments or 0,
            "digisilver_enrollments": report.digisilver_enrollments or 0,
        }
    else:
        metric_data = {
            "value": float(report.total_revenue or report.sales_amount or 0)
        }

    return {
        "query_type": "BRANCH_METRIC",
        "branch": b_name,
        "metric": metric,
        "date": str(query_date),
        "status": report.status or "SUBMITTED",
        "data": metric_data
    }


async def _query_total_metric(db: AsyncSession, metric: str, query_date: date) -> dict:
    """Fetch total aggregate and per-branch breakdown for a specific metric across all reporting branches."""
    reports_res = await db.execute(
        select(DailyReport, Branch)
        .join(Branch, DailyReport.branch_id == Branch.id)
        .where(DailyReport.date == query_date)
    )
    rows = reports_res.all()

    total_val = 0.0
    breakdown = []

    for report, branch in rows:
        b_name = _short_name(branch.name)
        val = 0.0
        if metric == "silver_sales":
            val = float(report.silver_sales or 0)
        elif metric == "gold_sales":
            val = float(report.gold_sales or 0)
        elif metric == "platinum_sales":
            val = float(report.platinum_sales or 0)
        elif metric == "diamond_sales":
            val = float(report.diamond_sales or 0)
        elif metric == "total_revenue":
            val = float(report.total_revenue or report.sales_amount or 0)

        total_val += val
        breakdown.append({"branch": b_name, "value": val})

    breakdown.sort(key=lambda x: x["value"], reverse=True)

    return {
        "query_type": "TOTAL_METRIC",
        "metric": metric,
        "date": str(query_date),
        "total_value": total_val,
        "branch_count": len(rows),
        "breakdown": breakdown
    }


# ─────────────────────────────────────────────
# Intent-Specific Handlers and State Machine Helpers
# ─────────────────────────────────────────────
import uuid

async def get_meeting_state(db: AsyncSession, conversation_id: uuid.UUID) -> Optional[dict]:
    from app.models.ai_memory import AIMemory
    state_key = f"meeting_creation_{conversation_id}"
    stmt = select(AIMemory).where(AIMemory.key == state_key)
    res = await db.execute(stmt)
    mem = res.scalars().first()
    return mem.value if mem else None

async def save_meeting_state(db: AsyncSession, conversation_id: uuid.UUID, state: dict):
    from app.models.ai_memory import AIMemory
    state_key = f"meeting_creation_{conversation_id}"
    stmt = select(AIMemory).where(AIMemory.key == state_key)
    res = await db.execute(stmt)
    mem = res.scalars().first()
    if not mem:
        mem = AIMemory(key=state_key, value=state)
        db.add(mem)
    else:
        mem.value = state
    await db.commit()

async def delete_meeting_state(db: AsyncSession, conversation_id: uuid.UUID):
    from app.models.ai_memory import AIMemory
    state_key = f"meeting_creation_{conversation_id}"
    stmt = select(AIMemory).where(AIMemory.key == state_key)
    res = await db.execute(stmt)
    mem = res.scalars().first()
    if mem:
        await db.delete(mem)
        await db.commit()

def get_next_question(state: dict) -> str:
    if not state.get("title"):
        return "Please provide the **meeting title**."
    if not state.get("date"):
        return "Could you specify the **date** for the meeting? (e.g. YYYY-MM-DD)"
    if not state.get("time"):
        return "What **time** should the meeting start? (e.g. HH:MM in 24h format, or 10am/3:30pm)"
    if not state.get("duration"):
        return "What is the **duration** of the meeting in minutes?"
    if not state.get("participants"):
        return "Who are the **participants** (names or branches) to invite?"
    if not state.get("branch"):
        return "Which **branch** is this meeting associated with? (e.g. Padi, Chromepet, Poonamallee, or 'all' for all branches)"
    return ""

async def _resolve_participants(db: AsyncSession, participants_list: list) -> list:
    """Resolve a list of names/roles/branches to User objects."""
    resolved_users = []
    if not participants_list:
        return resolved_users
        
    for p in participants_list:
        p_clean = str(p).lower().strip()
        stmt = select(User)
        res = await db.execute(stmt)
        users = res.scalars().all()
        
        matched_user = None
        for u in users:
            if p_clean in u.full_name.lower() or p_clean in u.email.lower():
                matched_user = u
                break
        
        if not matched_user:
            # Check branch manager role e.g. "Padi manager"
            for u in users:
                if u.role == "MANAGER" and u.branch_id:
                    br_stmt = select(Branch).where(Branch.id == u.branch_id)
                    br_res = await db.execute(br_stmt)
                    br = br_res.scalars().first()
                    if br and (p_clean in br.name.lower() or p_clean in br.code.lower()):
                        matched_user = u
                        break
                        
        if matched_user:
            resolved_users.append(matched_user)
            
    return resolved_users


class BaseIntentHandler:
    async def handle(
        self,
        db: AsyncSession,
        slots: Any,
        query: str,
        query_date: date,
        date_label: str,
        current_user: Optional[User] = None,
        conversation_id: Optional[uuid.UUID] = None,
    ) -> Any:
        raise NotImplementedError()


class BranchMetricHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        return await _query_branch_metric(db, slots.branch or "Padi", slots.metric or "attendance", query_date)


class GetBranchReportHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        return await _query_branch_report(db, slots.branch or "Padi", query_date)


class GetBranchRevenueHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        if slots.branch:
            return await _query_branch_metric(db, slots.branch, "total_revenue", query_date)
        return await _query_today_revenue(db, query_date)


class GetGoldSalesHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        if slots.branch:
            return await _query_branch_metric(db, slots.branch, "gold_sales", query_date)
        return await _query_gold_sales(db, query_date)


class GetSilverSalesHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        if slots.branch:
            return await _query_branch_metric(db, slots.branch, "silver_sales", query_date)
        return await _query_total_metric(db, "silver_sales", query_date)


class GetAttendanceHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        if slots.branch:
            return await _query_branch_metric(db, slots.branch, "attendance", query_date)
        res = await _query_attendance(db, query_date)
        if slots.intent == "TOTAL_ABSENTEES" or "absent" in query.lower():
            res["focus"] = "absentees"
        return res


class GetPendingReportsHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        return await _query_pending_reports(db, query_date)


class GetTopBranchHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        return await _query_top_branch(db, query_date)


class GetTopExecutiveHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        return await _query_top_performer(db, query_date, slots.branch)


class CompareBranchesHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        branches_res = await db.execute(select(Branch))
        all_branches = branches_res.scalars().all()

        q_lower = query.lower()
        matched = [b for b in all_branches if b.name.split(' ')[0].lower() in q_lower or b.code.lower() in q_lower]
        
        if len(matched) < 2 and slots.branches:
            matched = []
            for bname in slots.branches:
                b_obj = await _find_branch_by_name(db, bname)
                if b_obj:
                    matched.append(b_obj)
        
        if len(matched) < 2:
            matched = all_branches

        reports_res = await db.execute(
            select(DailyReport).where(DailyReport.date == query_date)
        )
        reports = reports_res.scalars().all()
        report_map = {r.branch_id: r for r in reports}

        # Verify BOTH reports exist
        for b in matched:
            if b.id not in report_map:
                short_b = _short_name(b.name)
                return f"{short_b} has not submitted {date_label}'s report, so a comparison cannot be generated."

        comparison = []
        for b in matched:
            r = report_map[b.id]
            comparison.append({
                "branch": _short_name(b.name),
                "status": "SUBMITTED",
                "total_revenue": float(r.total_revenue or r.sales_amount or 0),
                "gold_sales": float(r.gold_sales or 0),
                "silver_sales": float(r.silver_sales or 0),
                "platinum_sales": float(r.platinum_sales or 0),
                "diamond_sales": float(r.diamond_sales or 0),
                "attendance": int(r.employees_present or r.attendance_count or 0),
                "absent": int(r.employees_absent or 0),
                "target_achievement": float(r.target_achievement or 0),
                "operational_issues": r.operational_issues or r.issues or "None",
                "remarks": r.remarks or "None",
            })

        return {
            "query_type": "COMPARISON",
            "date": str(query_date),
            "branches": comparison
        }


class CreateMeetingHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        if not conversation_id:
            return "I couldn't identify the chat session to schedule the meeting, Sir."

        q_lower = query.lower()
        if any(w in q_lower for w in ["cancel", "stop", "abort", "cancel scheduling"]):
            await delete_meeting_state(db, conversation_id)
            return "Meeting scheduling has been cancelled, Sir. How else can I assist you?"

        state = await get_meeting_state(db, conversation_id)
        if not state:
            state = {
                "title": None,
                "date": None,
                "time": None,
                "duration": None,
                "participants": None,
                "branch": None,
                "notes": None
            }
            await save_meeting_state(db, conversation_id, state)

        # Retrieve chat history to extract parameters
        from app.models.conversation import AIMessage
        stmt = select(AIMessage).where(AIMessage.conversation_id == conversation_id).order_by(AIMessage.created_at.asc())
        res = await db.execute(stmt)
        messages = res.scalars().all()
        chat_log = "\n".join([f"{m.role.capitalize()}: {m.content}" for m in messages])

        from app.services.gemini_service import gemini_service
        extracted = await gemini_service.extract_meeting_slots(chat_log)
        print(f"[MEETING_HANDLER] Extracted from Groq: {extracted}")
        print(f"[MEETING_HANDLER] State before merge: {state}")

        # If Groq extraction failed (rate limit), do basic regex extraction
        # Only extract the NEXT missing field based on what we're asking for
        if not extracted:
            import re as _re
            last_user_text = ""
            for m in reversed(messages):
                if m.role == "user":
                    last_user_text = m.content
                    break

            # Determine what field is being asked for based on missing fields
            _asked_field = None
            if not state.get("title"):
                _asked_field = "title"
            elif not state.get("date"):
                _asked_field = "date"
            elif not state.get("time"):
                _asked_field = "time"
            elif not state.get("duration"):
                _asked_field = "duration"
            elif not state.get("participants"):
                _asked_field = "participants"
            elif not state.get("branch"):
                _asked_field = "branch"
            elif not state.get("notes"):
                _asked_field = "notes"

            last_lower = last_user_text.lower().strip()
            skip_words = {"no", "none", "ok", "okay", "yes", "all", "skip", "done", "go", "proceed"}

            if _asked_field == "title":
                # Title: user's last message as-is
                # BUT skip if it's a meeting-creation command (e.g. "add meeting tomorrow 3pm to 4pm")
                _meeting_cmd_kw = ("add meeting", "create meeting", "schedule meeting", "arrange meeting",
                                   "set up meeting", "new meeting", "plan meeting", "book meeting")
                is_meeting_cmd = any(last_lower.startswith(kw) for kw in _meeting_cmd_kw)
                if not is_meeting_cmd and last_lower not in skip_words and not last_lower.replace(".", "").replace(",", "").isdigit() and len(last_user_text.strip()) > 0:
                    extracted["title"] = last_user_text.strip()

            elif _asked_field == "duration":
                # Duration: extract number + unit
                dur_match = _re.search(r"(\d+)\s*(min|minute|hour|hr)", last_lower)
                if dur_match:
                    num = int(dur_match.group(1))
                    if "hour" in dur_match.group(2) or "hr" in dur_match.group(2):
                        num *= 60
                    extracted["duration"] = num
                elif last_lower.isdigit():
                    extracted["duration"] = int(last_lower)

            elif _asked_field == "participants":
                # Participants: take the message as participant description
                if last_lower not in skip_words:
                    extracted["participants"] = [last_user_text.strip()]

            elif _asked_field == "branch":
                # Branch: "all" or specific branch name
                if last_lower == "all":
                    extracted["branch"] = "all"
                else:
                    from app.services.intent_classifier import extract_branch_name
                    branch = extract_branch_name(last_user_text)
                    if branch:
                        extracted["branch"] = branch

            elif _asked_field == "notes":
                # Notes: skip phrases or take as notes
                if last_lower in skip_words or any(last_lower.startswith(p) for p in skip_words):
                    extracted["notes"] = "None"
                elif len(last_user_text.strip()) > 0:
                    extracted["notes"] = last_user_text.strip()

            if extracted:
                print(f"[MEETING_HANDLER] Regex fallback extraction: {extracted}")

        # Merge extracted values into state — fill gaps only (don't overwrite user-provided values).
        # Groq sees full chat history and may hallucinate/infer fields the user hasn't said yet.
        for k in ["title", "date", "time", "duration", "participants", "branch", "notes"]:
            val = extracted.get(k)
            if val is not None and val != "" and val != []:
                if isinstance(val, list) and not val:
                    continue
                existing = state.get(k)
                if existing is None or existing == "" or existing == []:
                    print(f"[MEETING_HANDLER] Filling {k} = {val!r}")
                    state[k] = val

        print(f"[MEETING_HANDLER] State after merge: {state}")

        # Detect the user's last message for skip/skip-optional-fields logic
        last_user_msg = ""
        for m in reversed(messages):
            if m.role == "user":
                last_user_msg = m.content.lower().strip()
                break

        print(f"[MEETING_HANDLER] Last user msg: '{last_user_msg}', notes in state: {state.get('notes')}")

        # Detect skip/proceed phrases — only apply to NOTES (the optional field)
        # Don't let "ok", "no", "go ahead" overwrite title/date/time/participants
        skip_phrases = ("no", "none", "no notes", "no agenda", "nil", "na", "nothing",
                        "nope", "nah", "do it", "go ahead", "proceed", "skip",
                        "that's all", "thats all", "that is all", "create it",
                        "just create", "schedule it", "just schedule", "finish",
                        "submit", "ok", "okay")

        if state.get("notes") is None or state.get("notes") == "" or state.get("notes") == []:
            if any(last_user_msg.startswith(p) for p in skip_phrases):
                print(f"[MEETING_HANDLER] Skip phrase detected for notes — setting notes to 'None'")
                state["notes"] = "None"

        await save_meeting_state(db, conversation_id, state)

        missing_fields = []
        for k in ["title", "date", "time", "duration", "participants", "branch"]:
            if state.get(k) is None or state.get(k) == "" or state.get(k) == []:
                missing_fields.append(k)

        print(f"[MEETING_HANDLER] Final state: {state}, missing_fields: {missing_fields}")

        if missing_fields:
            next_q = get_next_question(state)
            return {
                "query_type": "CREATE_MEETING_PROMPT",
                "state": state,
                "next_question": next_q,
                "missing_fields": missing_fields
            }

        # All fields collected! Default notes if not provided
        if not state.get("notes"):
            state["notes"] = "None"

        # Save meeting
        try:
            start_str = f"{state['date']} {state['time']}"
            start_time = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
            start_time = start_time.replace(tzinfo=timezone.utc)
        except Exception:
            try:
                state_date = state['date'].split("T")[0] if "T" in state['date'] else state['date']
                start_time = datetime.strptime(f"{state_date} {state['time']}", "%Y-%m-%d %H:%M")
                start_time = start_time.replace(tzinfo=timezone.utc)
            except Exception:
                start_time = datetime.now(timezone.utc)

        try:
            duration_mins = int(state["duration"])
        except (ValueError, TypeError):
            duration_mins = 60

        end_time = start_time + timedelta(minutes=duration_mins)

        # Resolve attendees
        resolved_attendees = []
        if isinstance(state["participants"], list):
            resolved_attendees = await _resolve_participants(db, state["participants"])
        elif isinstance(state["participants"], str):
            resolved_attendees = await _resolve_participants(db, [state["participants"]])

        # Resolve branch
        branch_obj = await _find_branch_by_name(db, state["branch"])
        branch_prefix = f"[{_short_name(branch_obj.name)}] " if branch_obj else ""

        db_meeting = Meeting(
            title=f"{branch_prefix}{state['title']}",
            agenda=state["notes"],
            start_time=start_time,
            end_time=end_time,
            organizer_id=current_user.id if current_user else None,
            status="SCHEDULED",
            notes=state["notes"],
            ai_summary=""
        )
        db_meeting.attendees = resolved_attendees
        db.add(db_meeting)
        await db.commit()
        await db.refresh(db_meeting)

        await delete_meeting_state(db, conversation_id)

        return {
            "query_type": "CREATE_MEETING_SUCCESS",
            "meeting": {
                "title": db_meeting.title,
                "date": db_meeting.start_time.strftime("%d-%b-%Y"),
                "time": db_meeting.start_time.strftime("%I:%M %p"),
                "duration": duration_mins,
                "branch": state["branch"],
                "participants": ", ".join([u.full_name for u in resolved_attendees]) if resolved_attendees else str(state["participants"]),
                "notes": db_meeting.notes
            }
        }


class UpdateMeetingHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        stmt = select(Meeting).where(and_(Meeting.organizer_id == current_user.id, Meeting.status == "SCHEDULED")).order_by(Meeting.start_time.asc())
        res = await db.execute(stmt)
        meetings = res.scalars().all()
        if not meetings:
            return {"query_type": "UPDATE_MEETING", "status": "NOT_FOUND", "message": "No scheduled meetings found that you organized, Sir."}
        
        target_meeting = None
        for m in meetings:
            if m.title.lower() in query.lower():
                target_meeting = m
                break
        if not target_meeting:
            target_meeting = meetings[0]
            
        target_meeting.notes = f"Updated via AI Assistant. {target_meeting.notes or ''}"
        await db.commit()
        await db.refresh(target_meeting)
        
        return {
            "query_type": "UPDATE_MEETING",
            "status": "SUCCESS",
            "meeting": {
                "title": target_meeting.title,
                "date": target_meeting.start_time.strftime("%d-%b-%Y"),
                "time": target_meeting.start_time.strftime("%I:%M %p"),
                "status": target_meeting.status
            }
        }


class DeleteMeetingHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        stmt = select(Meeting).where(and_(Meeting.organizer_id == current_user.id, Meeting.status == "SCHEDULED")).order_by(Meeting.start_time.asc())
        res = await db.execute(stmt)
        meetings = res.scalars().all()
        if not meetings:
            return {"query_type": "DELETE_MEETING", "status": "NOT_FOUND", "message": "No scheduled meetings found to cancel, Sir."}
            
        target_meeting = None
        for m in meetings:
            if m.title.lower() in query.lower():
                target_meeting = m
                break
        if not target_meeting:
            target_meeting = meetings[0]
            
        target_meeting.status = "CANCELLED"
        await db.commit()
        await db.refresh(target_meeting)
        
        return {
            "query_type": "DELETE_MEETING",
            "status": "SUCCESS",
            "meeting_title": target_meeting.title,
            "message": f"Meeting '{target_meeting.title}' has been successfully cancelled, Sir."
        }


class ShowTodaysAgendaHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        return await _query_agenda(db, current_user.id if current_user else None, query_date)


class ShowAlertsHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        if slots.branch:
            return await _query_branch_metric(db, slots.branch, "complaints", query_date)
        return await _query_complaints(db, query_date)


class ShowOperationalIssuesHandler(BaseIntentHandler):
    async def handle(self, db, slots, query, query_date, date_label, current_user, conversation_id):
        if slots.branch:
            return await _query_branch_metric(db, slots.branch, "issues", query_date)
        return await _query_alerts(db, query_date)


HANDLERS = {
    BusinessIntent.GET_BRANCH_REPORT: GetBranchReportHandler(),
    BusinessIntent.GET_BRANCH_REVENUE: GetBranchRevenueHandler(),
    BusinessIntent.GET_GOLD_SALES: GetGoldSalesHandler(),
    BusinessIntent.GET_SILVER_SALES: GetSilverSalesHandler(),
    BusinessIntent.GET_ATTENDANCE: GetAttendanceHandler(),
    BusinessIntent.GET_PENDING_REPORTS: GetPendingReportsHandler(),
    BusinessIntent.GET_TOP_BRANCH: GetTopBranchHandler(),
    BusinessIntent.GET_TOP_EXECUTIVE: GetTopExecutiveHandler(),
    BusinessIntent.COMPARE_BRANCHES: CompareBranchesHandler(),
    BusinessIntent.CREATE_MEETING: CreateMeetingHandler(),
    BusinessIntent.UPDATE_MEETING: UpdateMeetingHandler(),
    BusinessIntent.DELETE_MEETING: DeleteMeetingHandler(),
    BusinessIntent.SHOW_TODAYS_AGENDA: ShowTodaysAgendaHandler(),
    BusinessIntent.SHOW_ALERTS: ShowOperationalIssuesHandler(),
    BusinessIntent.SHOW_COMPLAINTS: ShowAlertsHandler(),
    BusinessIntent.SHOW_OPERATIONAL_ISSUES: ShowOperationalIssuesHandler(),
    
    # Legacy Support
    "BRANCH_REPORT": GetBranchReportHandler(),
    "BRANCH_METRIC": BranchMetricHandler(),
    "TOTAL_ABSENTEES": GetAttendanceHandler(),
    "ATTENDANCE": GetAttendanceHandler(),
    "TOTAL_REVENUE": GetBranchRevenueHandler(),
    "TODAY_REVENUE": GetBranchRevenueHandler(),
    "TOTAL_METRIC": GetBranchRevenueHandler(),
    "TOP_PERFORMER": GetTopExecutiveHandler(),
    "TOP_BRANCH": GetTopBranchHandler(),
    "REPORT_STATUS": ShowTodaysAgendaHandler(),
    "PENDING_REPORTS": GetPendingReportsHandler(),
    "SUBMITTED_REPORTS": ShowTodaysAgendaHandler(),
    "ALERTS": ShowOperationalIssuesHandler(),
    "COMPLAINTS": ShowAlertsHandler(),
    "REMARKS": GetBranchReportHandler(),
    "COMPARISON": CompareBranchesHandler(),
    "DIGIGOLD": GetBranchReportHandler(),
    "GOLD_SALES": GetGoldSalesHandler(),
    "DIAMOND_SALES": GetBranchReportHandler(),
    "AGENDA": ShowTodaysAgendaHandler(),
    "MEETINGS": ShowTodaysAgendaHandler(),
    "TASKS": ShowTodaysAgendaHandler(),
}

INTENT_HANDLERS = HANDLERS


# ─────────────────────────────────────────────
# Response Formatting
# ─────────────────────────────────────────────

def _format_deterministic(data: dict) -> str:
    """
    Deterministic response formatting fallback.
    Used when OpenAI API key is not configured.
    """
    qt = data.get("query_type", "")

    if data.get("message") and not data.get("submitted") and not data.get("pending") and not data.get("breakdown") and qt not in ("UPDATE_MEETING", "DELETE_MEETING"):
        return data["message"]

    if qt == "REPORT_STATUS":
        lines = [f"### Branch Report Status for {data['date']}:", ""]
        lines.append(f"• **Submitted**: {data['submitted_count']} of {data['total_branches']} branches")
        lines.append(f"• **Pending**: {data['pending_count']} branches")
        if data["submitted"]:
            lines.append("")
            lines.append("**Submitted Branches:**")
            for s in data["submitted"]:
                lines.append(f"• **{s['branch']}** — {_fmt_currency(s['revenue'])} (at {s['time']})")
        if data["pending"]:
            lines.append("")
            lines.append("**Pending Branches:**")
            for p in data["pending"]:
                lines.append(f"• {p}")
        return "\n".join(lines)

    elif qt == "BRANCH_REPORT":
        if "error" in data:
            return data["error"]
        if data.get("status") == "NOT_SUBMITTED":
            return data.get("message", f"No report submitted for {data.get('branch')}.")
        d = data
        
        parts = [f"Here is the daily executive summary report for {d['branch']} Swarna Mahal on {d['date']}:"]
        
        metrics_mapping = {
            "total_revenue": ("Revenue", lambda v: _fmt_currency(v)),
            "gold_sales": ("Gold", lambda v: _fmt_currency(v)),
            "silver_sales": ("Silver", lambda v: _fmt_currency(v)),
            "platinum_sales": ("Platinum", lambda v: _fmt_currency(v)),
            "diamond_sales": ("Diamond", lambda v: _fmt_currency(v)),
            "digigold_enrollments": ("DigiGold", lambda v: f"{v} enrollments"),
            "digisilver_enrollments": ("DigiSilver", lambda v: f"{v} enrollments"),
            "customer_complaints": ("Complaints", lambda v: str(v)),
            "operational_issues": ("Operational Issues", lambda v: str(v)),
            "manager_remarks": ("Manager Remarks", lambda v: str(v)),
        }
        
        if "employees_present" in d:
            parts.append(f"Attendance: {d['employees_present']} present, {d.get('employees_absent', 0)} absent")
            
        for key, (label, formatter) in metrics_mapping.items():
            if key in d:
                parts.append(f"{label}: {formatter(d[key])}")
                
        return "\n".join(parts)

    elif qt == "BRANCH_METRIC":
        if data.get("status") in ("NOT_SUBMITTED", "NOT_FOUND"):
            return data.get("message", f"No report submitted for {data.get('branch')}.")
        
        b = data["branch"]
        m = data["metric"]
        d = data.get("data", {})

        if m == "attendance":
            return (
                f"### {b} Staff Attendance ({data['date']}):\n\n"
                f"• **Present**: {d.get('present', 0)} employees\n"
                f"• **Absent**: {d.get('absent', 0)} employees"
            )
        elif m == "gold_sales":
            return (
                f"### {b} Gold Sales ({data['date']}):\n\n"
                f"• **Gold Sales**: {_fmt_currency(d.get('gold_sales', 0))}"
            )
        elif m == "silver_sales":
            return (
                f"### {b} Silver Sales ({data['date']}):\n\n"
                f"• **Silver Sales**: {_fmt_currency(d.get('silver_sales', 0))}"
            )
        elif m == "platinum_sales":
            return (
                f"### {b} Platinum Sales ({data['date']}):\n\n"
                f"• **Platinum Sales**: {_fmt_currency(d.get('platinum_sales', 0))}"
            )
        elif m == "diamond_sales":
            return (
                f"### {b} Diamond Sales ({data['date']}):\n\n"
                f"• **Diamond Sales**: {_fmt_currency(d.get('diamond_sales', 0))}"
            )
        elif m == "total_revenue":
            return (
                f"### {b} Total Revenue ({data['date']}):\n\n"
                f"• **Total Revenue**: {_fmt_currency(d.get('total_revenue', 0))}"
            )
        elif m == "complaints":
            return (
                f"### {b} Customer Complaints ({data['date']}):\n\n"
                f"• **Complaints**: \"{d.get('customer_complaints', 'None reported')}\""
            )
        elif m == "issues":
            return (
                f"### {b} Operational Issues ({data['date']}):\n\n"
                f"• **Issues**: {d.get('operational_issues', 'None reported')}"
            )
        elif m == "remarks":
            return (
                f"### {b} Manager Remarks ({data['date']}):\n\n"
                f"• **Remarks**: \"{d.get('manager_remarks', 'None recorded')}\""
            )
        elif m == "digigold":
            return (
                f"### {b} Digital Scheme Enrollments ({data['date']}):\n\n"
                f"• **DigiGold**: {d.get('digigold_enrollments', 0)} enrollments\n"
                f"• **DigiSilver**: {d.get('digisilver_enrollments', 0)} enrollments"
            )
        else:
            return f"### {b} {m.title()} ({data['date']}):\n\n{json.dumps(d)}"

    elif qt == "TOTAL_METRIC":
        m_title = data["metric"].replace("_", " ").title()
        lines = [
            f"### Total {m_title} Summary for {data['date']}:\n",
            f"• **Total {m_title}**: {_fmt_currency(data['total_value'])}",
            f"• **Reporting Branches**: {data['branch_count']}",
        ]
        if data.get("breakdown"):
            lines.append(f"\n**Branch {m_title} Breakdown:**")
            for b in data["breakdown"]:
                lines.append(f"• **{b['branch']}**: {_fmt_currency(b['value'])}")
        return "\n".join(lines)

    elif qt == "PENDING_REPORTS":
        if not data["pending"]:
            return f"All {data['total_branches']} Pothys branches have submitted their reports for {data['date']}, Sir."
        branch_list = "\n".join(f"• {name}" for name in data["pending"])
        return f"The following {data['pending_count']} branches have **pending reports** for {data['date']}, Sir:\n\n{branch_list}"

    elif qt == "SUBMITTED_REPORTS":
        if not data["submitted"]:
            return f"No daily reports have been submitted for {data['date']} yet, Sir."
        lines = [f"The following {data['submitted_count']} branches have **successfully submitted** their reports for {data['date']}, Sir:\n"]
        for s in data["submitted"]:
            lines.append(f"• {s['branch']} (at {s['time']})")
        return "\n".join(lines)

    elif qt == "GOLD_SALES":
        lines = [
            f"### Gold Sales Summary for {data['date']}:\n",
            f"• **Total Gold Sales**: {_fmt_currency(data.get('total_gold_sales', 0))}",
            f"• **Top Gold Sales Branch**: **{data.get('top_branch', 'N/A')}** ({_fmt_currency(data.get('top_gold_sales', 0))})",
        ]
        if data.get("breakdown"):
            lines.append("\n**Branch Gold Sales Breakdown:**")
            for b in data["breakdown"]:
                lines.append(f"• **{b['branch']}**: {_fmt_currency(b['gold_sales'])}")
        return "\n".join(lines)

    elif qt == "DIAMOND_SALES":
        if "message" in data and not data.get("employee"):
            return data["message"]
        return (
            f"Top Diamond Sales Performer for **{data['date']}** is **{data['employee']}** at "
            f"**{data['branch']} Swarna Mahal** with a diamond sales volume of **{_fmt_currency(data['diamond_amount'])}**."
        )

    elif qt == "DIGIGOLD":
        if "message" in data and not data.get("employee"):
            return data["message"]
        return (
            f"Top DigiGold Scheme Enroller for **{data['date']}** is **{data['employee']}** at "
            f"**{data['branch']} Swarna Mahal** with **{data['digigold_enrollments']} DigiGold** and "
            f"**{data['digisilver_enrollments']} DigiSilver** scheme enrollments."
        )

    elif qt == "TOP_BRANCH":
        lines = [
            f"**{data['branch']}** is the top performing branch today with a total revenue of "
            f"**{_fmt_currency(data['total_revenue'])}**.\n\n"
            f"**Sales Breakdown:**\n"
            f"- **Gold**: {_fmt_currency(data.get('gold_sales'))}\n"
            f"- **Silver**: {_fmt_currency(data.get('silver_sales'))}\n"
            f"- **Platinum**: {_fmt_currency(data.get('platinum_sales'))}\n"
            f"- **Diamond**: {_fmt_currency(data.get('diamond_sales'))}"
        ]
        if data.get("rankings"):
            lines.append("\n**All Reporting Branches Revenue Ranking:**")
            for r in data["rankings"]:
                lines.append(f"• **{r['branch']}**: {_fmt_currency(r['revenue'])}")
        return "\n".join(lines)

    elif qt == "TOP_PERFORMER":
        lines = [
            f"The best performing employee today is **{data['employee_name']}** "
            f"({data.get('designation', 'Executive')}) at **{data['branch']} Swarna Mahal** "
            f"with a total sales volume of **{_fmt_currency(data['total_sales'])}**.\n\n"
            f"**Sales Breakdown:**\n"
            f"- **Gold**: {_fmt_currency(data.get('gold_amount') or data.get('gold', 0))}\n"
            f"- **Silver**: {_fmt_currency(data.get('silver_amount') or data.get('silver', 0))}\n"
            f"- **Platinum**: {_fmt_currency(data.get('platinum_amount') or data.get('platinum', 0))}\n"
            f"- **Diamond**: {_fmt_currency(data.get('diamond_amount') or data.get('diamond', 0))}"
        ]
        if data.get("all_performers") and len(data["all_performers"]) > 1:
            lines.append("\n**Executive Performance Leaderboard:**")
            for p in data["all_performers"]:
                lines.append(f"• **{p['employee_name']}** ({p['branch']}): {_fmt_currency(p['total_sales'])}")
        return "\n".join(lines)

    elif qt == "TODAY_REVENUE":
        lines = [
            f"### Revenue Summary for {data['date']}:\n",
            f"• **Total Revenue**: {_fmt_currency(data['total_revenue'])}",
            f"• **Gold Sales**: {_fmt_currency(data.get('gold_sales', 0))}",
            f"• **Silver Sales**: {_fmt_currency(data.get('silver_sales', 0))}",
            f"• **Platinum Sales**: {_fmt_currency(data.get('platinum_sales', 0))}",
            f"• **Diamond Sales**: {_fmt_currency(data.get('diamond_sales', 0))}",
            f"• **Reporting Branches**: {data['branch_count']}",
            "\n**Branch Revenue Breakdown:**"
        ]
        for b in data["breakdown"]:
            lines.append(f"• **{b['branch']}**: {_fmt_currency(b['revenue'])} ({b['target_achievement']:.1f}% target achieved)")
        return "\n".join(lines)

    elif qt == "ATTENDANCE":
        lines = [
            f"### Staff Attendance Summary for {data['date']}:\n",
            f"• **Total Present**: {data['total_present']} employees",
            f"• **Total Absentees**: {data['total_absent']} employees",
            f"• **Reporting Branches**: {data['branch_count']}",
            "\n**Branch Attendance Breakdown:**"
        ]
        for b in data["breakdown"]:
            lines.append(f"• **{b['branch']}**: {b['present']} present, {b['absent']} absent")
        return "\n".join(lines)

    elif qt == "COMPLAINTS":
        if not data["complaints"]:
            return f"All branches report customer satisfaction. No pending complaints for {data['date']}, Sir."
        lines = [
            f"### Customer Complaints Summary ({data['date']}):\n",
            f"• **Total Complaints**: {data['count']}",
            "\n**Complaint Details:**"
        ]
        for c in data["complaints"]:
            lines.append(f"• **{c['branch']}**: \"{c['complaint']}\"")
        return "\n".join(lines)

    elif qt == "ALERTS":
        if not data["alerts"]:
            return f"No operational alerts or issues have been reported for {data['date']}, Sir."
        lines = [
            f"### Operational Alerts & Issues ({data['date']}):\n",
            f"• **Total Alerts**: {data['count']}",
            "\n**Alert Details:**"
        ]
        for a in data["alerts"]:
            lines.append(f"• **{a['branch']}**: {a['issue']}")
        return "\n".join(lines)

    elif qt == "REMARKS":
        if not data["remarks"]:
            return f"No manager remarks or feedback have been submitted for {data['date']}, Sir."
        lines = [f"### Branch Manager Remarks ({data['date']}):"]
        for r in data["remarks"]:
            lines.append(f"• **{r['branch']}**: \"{r['remark']}\"")
        return "\n".join(lines)

    elif qt == "AGENDA":
        lines = [f"### Today's Agenda Summary ({data['date']}):\n"]
        lines.append(f"• {data['meetings_count']} meetings scheduled today." if data['meetings_count'] else "• No meetings scheduled today.")
        lines.append(f"• {data['tasks_count']} pending executive tasks." if data['tasks_count'] else "• No pending executive tasks.")
        lines.append(f"• {data['pending_reports']} branch reports are still pending." if data['pending_reports'] else "• All branch reports have been submitted.")
        lines.append(f"• {data['alerts_count']} operational alerts reported." if data['alerts_count'] else "• No operational alerts.")
        return "\n".join(lines)

    elif qt == "MEETINGS":
        if not data["meetings"]:
            return "No meetings scheduled in the calendar, Sir."
        lines = ["Corporate & Branch Meetings Schedule:\n"]
        for m in data["meetings"]:
            lines.append(f"• **{m['title']}** ({m['date']} at {m['time']}):\n  - Agenda: {m['agenda']}\n  - Status: {m['status']}")
        return "\n\n".join(lines)

    elif qt == "TASKS":
        if not data["tasks"]:
            return "No tasks are currently registered, Sir."
        lines = ["Operations Tasks & Actions List:\n"]
        for t in data["tasks"]:
            lines.append(f"• **{t['title']}** (Due: {t['due_date']}):\n  - Priority: {t['priority']} | Status: {t['status']}\n  - Description: {t['description']}")
        return "\n\n".join(lines)

    elif qt == "COMPARISON":
        parts = [f"Branch Performance Comparison for {data['date']}:"]
        for b in data["branches"]:
            if b["status"] == "SUBMITTED":
                b_parts = [f"{b['branch']}:"]
                
                metrics_mapping = {
                    "total_revenue": ("Total Revenue", lambda v: _fmt_currency(v)),
                    "gold_sales": ("Gold", lambda v: _fmt_currency(v)),
                    "silver_sales": ("Silver", lambda v: _fmt_currency(v)),
                    "platinum_sales": ("Platinum", lambda v: _fmt_currency(v)),
                    "diamond_sales": ("Diamond", lambda v: _fmt_currency(v)),
                    "target_achievement": ("Target Achievement", lambda v: f"{v:.1f}%"),
                    "operational_issues": ("Operational Issues", lambda v: str(v)),
                    "remarks": ("Remarks", lambda v: str(v)),
                }
                
                if "attendance" in b:
                    b_parts.append(f"Staff Attendance: {b['attendance']} present, {b.get('absent', 0)} absent")
                    
                for key, (label, formatter) in metrics_mapping.items():
                    if key in b:
                        b_parts.append(f"{label}: {formatter(b[key])}")
                        
                parts.append("\n".join(f"  - {line}" if idx > 0 else line for idx, line in enumerate(b_parts)))
            else:
                parts.append(f"{b['branch']}: No report submitted yet.")
        return "\n\n".join(parts)

    elif qt == "CREATE_MEETING_PROMPT":
        state = data.get("state", {})
        collected = []
        for k, v in state.items():
            if v:
                collected.append(f"• **{k.capitalize()}**: {v}")
        collected_str = "\n".join(collected) if collected else "None"
        return f"To schedule the meeting, I still need some details, Sir.\n\n**Collected Details:**\n{collected_str}\n\n{data.get('next_question')}"

    elif qt == "CREATE_MEETING_SUCCESS":
        m = data.get("meeting", {})
        return (
            f"### Meeting Scheduled Successfully, Sir.\n\n"
            f"• **Title**: {m.get('title')}\n"
            f"• **Date**: {m.get('date')}\n"
            f"• **Time**: {m.get('time')}\n"
            f"• **Duration**: {m.get('duration')} minutes\n"
            f"• **Participants**: {m.get('participants')}\n"
            f"• **Branch**: {m.get('branch')}\n"
            f"• **Notes**: {m.get('notes')}"
        )

    elif qt == "UPDATE_MEETING":
        if data.get("status") == "NOT_FOUND":
            return data["message"]
        return f"Meeting '{data['meeting']['title']}' has been updated successfully for {data['meeting']['date']} at {data['meeting']['time']}, Sir."

    elif qt == "DELETE_MEETING":
        return data.get("message", "Meeting cancelled successfully.")

    # Generic fallback
    return json.dumps(data, indent=2, default=str)


def filter_metrics_by_slots(data: dict, slots: Optional[Any]) -> dict:
    """If specific metrics were requested in slots, filter the database result to only include those."""
    if not slots or not slots.metrics:
        return data
        
    qt = data.get("query_type", "")
    if qt in ("CREATE_MEETING_PROMPT", "CREATE_MEETING_SUCCESS", "UPDATE_MEETING", "DELETE_MEETING", "AGENDA", "MEETINGS", "TASKS", "PENDING_REPORTS"):
        return data
        
    filtered = {
        "query_type": qt,
        "branch": data.get("branch"),
        "date": data.get("date"),
        "status": data.get("status")
    }
    if data.get("message") is not None:
        filtered["message"] = data["message"]
    if data.get("submitted") is not None:
        filtered["submitted"] = data["submitted"]
    if data.get("branches") is not None:
        filtered["branches"] = data["branches"]
    
    has_any = False
    for metric in slots.metrics:
        if metric in data:
            filtered[metric] = data[metric]
            has_any = True
        elif metric == "attendance" and "employees_present" in data:
            filtered["employees_present"] = data["employees_present"]
            filtered["employees_absent"] = data["employees_absent"]
            has_any = True
            
    if qt == "COMPARISON" and data.get("branches"):
        filtered_branches = []
        for b_data in data["branches"]:
            b_filtered = {
                "branch": b_data.get("branch"),
                "status": b_data.get("status"),
                "target_achievement": b_data.get("target_achievement"),
                "remarks": b_data.get("remarks"),
                "operational_issues": b_data.get("operational_issues")
            }
            for metric in slots.metrics:
                if metric in b_data:
                    b_filtered[metric] = b_data[metric]
                    has_any = True
                elif metric == "attendance" and "attendance" in b_data:
                    b_filtered["attendance"] = b_data["attendance"]
                    b_filtered["absent"] = b_data["absent"]
                    has_any = True
            filtered_branches.append(b_filtered)
        filtered["branches"] = filtered_branches

    if not has_any:
        return data
        
    return filtered


def strip_markdown(text: str) -> str:
    """Strip all markdown formatting tokens from text, ensuring pure plain text."""
    if not text:
        return ""
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'_+', '', text)
    text = re.sub(r'#+\s*(.*?)\n', r'\1\n', text)
    text = re.sub(r'#+\s*(.*?)$', r'\1', text)
    text = re.sub(r'`+', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


async def _format_with_llm(query: str, data: dict, slots: Optional[Any] = None) -> str:
    """Format structured data into a professional executive response using Gemini API with automatic fallback."""
    filtered_data = filter_metrics_by_slots(data, slots)
    try:
        from app.services.gemini_service import gemini_service
        gemini_response = await gemini_service.format_executive_response(query, filtered_data)
        if gemini_response:
            return gemini_response
    except Exception as e:
        logger.warning(f"Gemini service execution error: {e}. Falling back to deterministic formatting.")

    return _format_deterministic(filtered_data)


# ─────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────

class BusinessQueryExecutor:
    """
    Main entry point for business queries.

    Usage:
        executor = BusinessQueryExecutor()
        response = await executor.execute(
            intent="BRANCH_REPORT",
            query="Show me Padi report",
            db=session,
            branch_name="Padi"
        )
    """

    @staticmethod
    async def execute(
        intent: str,
        query: str,
        db: AsyncSession,
        branch_name: Optional[str] = None,
        current_user: Optional[Any] = None,
        conversation_id: Optional[uuid.UUID] = None,
        pre_classified_slots: Optional[Any] = None,
        **kwargs: Any,
    ) -> str:
        """Execute a business query based on structured slot extraction."""
        if pre_classified_slots:
            slots = pre_classified_slots
        else:
            from app.services.intent_classifier import intent_classifier
            slots = await intent_classifier.classify_slots_async(query)
        print(f"[BUSINESS_EXECUTOR] Extracted Slots: {slots.to_dict()}")

        query_date = date.today()
        date_label = "today"
        if slots.time == "yesterday":
            query_date = date.today() - timedelta(days=1)
            date_label = "yesterday"

        try:
            # Override slots.intent if conversation has active meeting creation flow
            if conversation_id:
                from app.models.ai_memory import AIMemory
                state_key = f"meeting_creation_{conversation_id}"
                stmt = select(AIMemory).where(AIMemory.key == state_key)
                res = await db.execute(stmt)
                mem = res.scalars().first()
                if mem:
                    slots.intent = BusinessIntent.CREATE_MEETING
            
            # Find matching handler
            handler = HANDLERS.get(slots.intent)
            if not handler:
                handler = ShowTodaysAgendaHandler()

            structured_data = await handler.handle(
                db=db,
                slots=slots,
                query=query,
                query_date=query_date,
                date_label=date_label,
                current_user=current_user,
                conversation_id=conversation_id
            )

            # If the handler returns a string directly (e.g. error/validation message)
            if isinstance(structured_data, str):
                return strip_markdown(structured_data)

            print(f"[BUSINESS_EXECUTOR] Query returned: {json.dumps(structured_data, default=str)[:200]}...")
            response = await _format_with_llm(query, structured_data, slots)
            print(f"[BUSINESS_EXECUTOR] Response formatted successfully.")
            return strip_markdown(response)

        except Exception as e:
            logger.error(f"Business query execution error: {e}", exc_info=True)
            # Never expose Python exceptions to the user
            return "I encountered a processing error while retrieving the business data. Please try again or contact support."


# Module-level singleton
business_executor = BusinessQueryExecutor()
