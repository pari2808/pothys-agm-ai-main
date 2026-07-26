import uuid
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.session import get_db
from app.api.deps import get_current_user, check_role
from app.models.user import User
from app.models.report import DailyReport
from app.repositories.branch import BranchRepository
from app.repositories.report import DailyReportRepository
from app.schemas.branch import BranchResponse

router = APIRouter()

@router.get("", response_model=List[dict])
async def list_branches_dashboard(
    report_date: Optional[date] = Query(None, description="Date to check operational status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["AGM"]))
):
    """
    List all branches with their operational status for a specific date (defaults to today).
    Only accessible by AGM to monitor operations at a glance.
    """
    branch_repo = BranchRepository(db)
    report_repo = DailyReportRepository(db)

    target_date = report_date
    if not target_date:
        today = date.today()
        reports_today = await report_repo.get_reports_for_date(today)
        if reports_today:
            target_date = today
        else:
            latest_stmt = select(DailyReport.date).where(DailyReport.date <= today).order_by(DailyReport.date.desc()).limit(1)
            res = await db.execute(latest_stmt)
            latest_date = res.scalar_one_or_none()
            target_date = latest_date or today

    branches = await branch_repo.get_all()
    reports = await report_repo.get_reports_for_date(target_date)

    print(f"[DASHBOARD LOG] /api/v1/branches - Executed SQL query for date '{target_date}'. Branches: {len(branches)}, Reports found: {len(reports)}")

    # Map report by branch_id
    reports_map = {r.branch_id: r for r in reports}

    result = []
    for branch in branches:
        report = reports_map.get(branch.id)
        result.append({
            "id": branch.id,
            "name": branch.name,
            "code": branch.code,
            "monthly_sales_target": float(branch.monthly_sales_target) if branch.monthly_sales_target else 0.0,
            "status": "SUBMITTED" if report else "PENDING",
            "report": {
                "id": report.id,
                "sales_amount": float(report.sales_amount or 0.0),
                "attendance_count": report.attendance_count or 0,
                "target_achievement": float(report.target_achievement or 0.0),
                "inventory_status": report.inventory_status or "None",
                "remarks": report.remarks or "None",
                "issues": report.issues or "None",
                "original_file_url": report.original_file_url,
                # New production template fields
                "gold": float(report.gold or 0.0),
                "diamond": float(report.diamond or 0.0),
                "platinum": float(report.platinum or 0.0),
                "silver": float(report.silver or 0.0),
                "gold_weight": report.gold_weight,
                "diamond_weight": report.diamond_weight,
                "platinum_weight": report.platinum_weight,
                "silver_weight": report.silver_weight,
                "silver_mrp": float(report.silver_mrp or 0.0),
                "total_revenue": float(report.total_revenue or 0.0),
                "digigold": report.digigold or 0,
                "digisilver": report.digisilver or 0,
                "digigold_enrollments": report.digigold_enrollments or 0,
                "digisilver_enrollments": report.digisilver_enrollments or 0,
                "employees_present": report.employees_present or 0,
                "employees_absent": report.employees_absent or 0,
                "customer_complaints": report.customer_complaints or "None",
                "operational_issues": report.operational_issues or "None"
            } if report else None
        })

    return result


@router.get("/dashboard-summary", response_model=dict)
async def get_dashboard_summary(
    report_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["AGM"]))
):
    """Retrieve aggregate summary analytics for the AGM dashboard from uploaded templates."""
    report_repo = DailyReportRepository(db)
    branch_repo = BranchRepository(db)

    target_date = report_date
    if not target_date:
        today = date.today()
        reports_today = await report_repo.get_reports_for_date(today)
        if reports_today:
            target_date = today
        else:
            latest_stmt = select(DailyReport.date).where(DailyReport.date <= today).order_by(DailyReport.date.desc()).limit(1)
            res = await db.execute(latest_stmt)
            latest_date = res.scalar_one_or_none()
            target_date = latest_date or today
    
    branches = await branch_repo.get_all()
    reports = await report_repo.get_reports_for_date(target_date)
    
    # 1. Aggregations using new field names
    total_rev = sum(float(r.total_revenue or r.sales_amount or 0.0) for r in reports)
    
    total_digigold = 0
    total_digisilver = 0
    from app.models.employee_performance import EmployeePerformance
    from sqlalchemy import func

    for r in reports:
        dg = r.digigold or 0
        ds = r.digisilver or 0
        if dg == 0 and ds == 0:
            emp_stmt = select(
                func.coalesce(func.sum(EmployeePerformance.digigold), 0),
                func.coalesce(func.sum(EmployeePerformance.digisilver), 0)
            ).where(EmployeePerformance.report_id == r.id)
            emp_res = await db.execute(emp_stmt)
            emp_row = emp_res.first()
            if emp_row:
                emp_dg, emp_ds = emp_row
                dg = int(emp_dg or 0)
                ds = int(emp_ds or 0)
        total_digigold += int(dg)
        total_digisilver += int(ds)
    
    emp_present = sum(r.employees_present or (r.attendance_count or 0) for r in reports)
    emp_absent = sum(r.employees_absent or 0 for r in reports)
    
    complaints = []
    for r in reports:
        if r.customer_complaints and r.customer_complaints.lower() != "none" and r.customer_complaints.strip():
            complaints.append(r.customer_complaints.strip())
            
    # 2. Top Performing Branch
    top_branch_name = "N/A"
    max_rev = -1.0
    branch_map = {b.id: b for b in branches}
    for r in reports:
        rev = float(r.total_revenue or r.sales_amount or 0.0)
        if rev > max_rev:
            max_rev = rev
            if r.branch_id in branch_map:
                top_branch_name = branch_map[r.branch_id].name.split(" ")[0]
                
    # 3. Top Performing Employee
    top_employee_str = "N/A"
    try:
        from app.models.employee import Employee
        from app.models.branch import Branch
        
        stmt = (
            select(EmployeePerformance, Employee, Branch)
            .join(Employee, EmployeePerformance.employee_id == Employee.id)
            .join(DailyReport, EmployeePerformance.report_id == DailyReport.id)
            .join(Branch, Employee.branch_id == Branch.id)
            .where(DailyReport.date == target_date)
            .order_by(
                (
                    func.coalesce(EmployeePerformance.gold, 0) +
                    func.coalesce(EmployeePerformance.silver, 0) +
                    func.coalesce(EmployeePerformance.platinum, 0) +
                    func.coalesce(EmployeePerformance.diamond, 0)
                ).desc()
            )
            .limit(1)
        )
        res = await db.execute(stmt)
        top_perf = res.first()
        if top_perf:
            perf, emp, b_obj = top_perf
            total_emp_sales = float(
                (perf.gold or 0.0) +
                (perf.silver or 0.0) +
                (perf.platinum or 0.0) +
                (perf.diamond or 0.0)
            )
            top_employee_str = f"{emp.name} ({b_obj.name.split(' ')[0]}) - Rs. {total_emp_sales:,.2f}"
    except Exception as e:
        print(f"[DASHBOARD WARNING] Failed to query top performing employee: {e}")
        top_employee_str = "N/A"

    print(f"[DASHBOARD LOG] /api/v1/branches/dashboard-summary - Target Date: '{target_date}', Reports count: {len(reports)}, Total Rev: {total_rev}, DigiGold Sum: {total_digigold}, DigiSilver Sum: {total_digisilver}")

    return {
        "total_revenue": float(total_rev),
        "digigold": total_digigold,
        "digisilver": total_digisilver,
        "digigold_enrollments": total_digigold,
        "digisilver_enrollments": total_digisilver,
        "employees_present": emp_present,
        "employees_absent": emp_absent,
        "complaints_count": len(complaints),
        "top_performing_branch": top_branch_name,
        "top_performing_employee": top_employee_str,
        "complaints": complaints
    }

@router.get("/{branch_id}/analytics", response_model=dict)
async def get_branch_analytics(
    branch_id: uuid.UUID,
    report_date: Optional[date] = Query(None, description="Specific date to fetch report for"),
    start_date: Optional[date] = Query(None, description="Start date for trends"),
    end_date: Optional[date] = Query(None, description="End date for trends"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["AGM", "MANAGER"]))
):
    """
    Get detailed metrics, charts, and operational trend details for a specific branch.
    AGM can view any branch; Branch Managers can only view their own branch.
    """
    if current_user.role == "MANAGER" and current_user.branch_id != branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are only authorized to access analytics for your own branch"
        )

    branch_repo = BranchRepository(db)
    branch = await branch_repo.get_by_id(branch_id)
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )

    # Determine target_date based on report_date parameter or latest available
    if report_date:
        # Specific date requested — use it exactly, no fallback
        target_date = report_date
    else:
        # Default: find the latest report date for THIS branch
        latest_date_stmt = (
            select(DailyReport.date)
            .where(DailyReport.branch_id == branch_id)
            .order_by(DailyReport.date.desc())
            .limit(1)
        )
        latest_date_res = await db.execute(latest_date_stmt)
        latest_date = latest_date_res.scalar_one_or_none()
        target_date = latest_date or date.today()

    start = start_date or (target_date - timedelta(days=30))
    end = end_date or target_date

    # Query reports in date range
    result = await db.execute(
        select(DailyReport)
        .where(
            and_(
                DailyReport.branch_id == branch_id,
                DailyReport.date >= start,
                DailyReport.date <= end
            )
        )
        .order_by(DailyReport.date.asc())
    )
    reports = result.scalars().all()

    # Calculations
    total_sales = sum(float(r.sales_amount or 0.0) for r in reports)
    avg_attendance = sum(r.attendance_count or 0 for r in reports) / len(reports) if reports else 0.0
    avg_achievement = sum(float(r.target_achievement or 0.0) for r in reports) / len(reports) if reports else 0.0
    
    # Check flags for issues requiring AGM attention
    issues_logged = [
        {"date": r.date, "manager": r.manager_id, "issues": r.issues}
        for r in reports if r.issues and r.issues.strip()
    ]

    trends = [
        {
            "date": r.date,
            "sales_amount": float(r.sales_amount or 0.0),
            "attendance_count": r.attendance_count or 0,
            "target_achievement": float(r.target_achievement or 0.0)
        }
        for r in reports
    ]

    # Fetch target_date's report details (including employee performances and scheme summary)
    from app.models.employee_performance import EmployeePerformance
    from app.models.employee import Employee
    from app.models.scheme_summary import SchemeSummary

    today_stmt = select(DailyReport).where(DailyReport.branch_id == branch_id, DailyReport.date == target_date)
    today_res = await db.execute(today_stmt)
    today_report = today_res.scalars().first()

    if not today_report and not report_date:
        # Fallback to the latest available report for THIS branch (only when no explicit date requested)
        today_stmt = select(DailyReport).where(DailyReport.branch_id == branch_id).order_by(DailyReport.date.desc()).limit(1)
        today_res = await db.execute(today_stmt)
        today_report = today_res.scalars().first()
        if today_report:
            target_date = today_report.date

    employee_performances_list = []
    top_performer_str = "N/A"
    scheme_sum_dict = {}

    if today_report:
        emp_perf_stmt = (
            select(EmployeePerformance, Employee)
            .join(Employee, EmployeePerformance.employee_id == Employee.id)
            .where(EmployeePerformance.report_id == today_report.id)
        )
        emp_perf_res = await db.execute(emp_perf_stmt)
        emp_perfs = emp_perf_res.all()

        max_emp_sales = -1.0
        for perf, emp in emp_perfs:
            emp_total_sales = float(
                (perf.gold or 0.0) +
                (perf.silver or 0.0) +
                (perf.platinum or 0.0) +
                (perf.diamond or 0.0)
            )
            if emp_total_sales > max_emp_sales:
                max_emp_sales = emp_total_sales
                top_performer_str = f"{emp.name} (₹{emp_total_sales:,.2f})"

            employee_performances_list.append({
                "employee_name": emp.name,
                "department": emp.designation,
                "designation": emp.designation,
                "gold": float(perf.gold or 0.0),
                "diamond": float(perf.diamond or 0.0),
                "platinum": float(perf.platinum or 0.0),
                "silver": float(perf.silver or 0.0),
                "silver_mrp": float(perf.silver_mrp or 0.0),
                "subhiksham_count": perf.subhiksham_count or 0,
                "subhiksham_value": float(perf.subhiksham_value or 0.0),
                "viruksham_count": perf.viruksham_count or 0,
                "viruksham_value": float(perf.viruksham_value or 0.0),
                "digigold": perf.digigold or 0,
                "digisilver": perf.digisilver or 0,
                "sales": emp_total_sales,
            })

        ss_stmt = select(SchemeSummary).where(SchemeSummary.report_id == today_report.id)
        ss_res = await db.execute(ss_stmt)
        ss_obj = ss_res.scalars().first()
        if ss_obj:
            scheme_sum_dict = {
                "subhiksham_count": ss_obj.subhiksham_count or 0,
                "subhiksham_value": float(ss_obj.subhiksham_value or 0.0),
                "viruksham_count": ss_obj.viruksham_count or 0,
                "viruksham_value": float(ss_obj.viruksham_value or 0.0),
                "digigold_total": ss_obj.digigold_total,
                "digisilver_total": ss_obj.digisilver_total,
                "digigold_revenue": ss_obj.digigold_revenue or 0.0,
                "digisilver_revenue": ss_obj.digisilver_revenue or 0.0,
                "scheme_items": ss_obj.scheme_items or [],
                "overall_remarks": ss_obj.overall_remarks or "None",
            }
        else:
            scheme_sum_dict = {
                "subhiksham_count": 0,
                "subhiksham_value": 0.0,
                "viruksham_count": 0,
                "viruksham_value": 0.0,
                "digigold_total": 0,
                "digisilver_total": 0,
                "digigold_revenue": 0.0,
                "digisilver_revenue": 0.0,
                "scheme_items": [],
                "overall_remarks": "None",
            }

    res_dict = {
        "report_date": str(target_date),
        "branch": {
            "id": branch.id,
            "name": branch.name,
            "code": branch.code,
            "monthly_sales_target": float(branch.monthly_sales_target) if branch.monthly_sales_target else 0.0
        },
        "summary": {
            "total_sales": float(total_sales),
            "average_attendance": round(avg_attendance, 1),
            "average_target_achievement": round(avg_achievement, 2),
            "reports_count": len(reports),
            "issues_count": len(issues_logged)
        },
        "trends": trends,
        "recent_issues": issues_logged,
        "today_report_details": {
            "employee_performances": employee_performances_list,
            "top_performer": top_performer_str,
            "scheme_summary": scheme_sum_dict,
            "report": {
                "id": today_report.id,
                "date": today_report.date,
                "sales_amount": float(today_report.sales_amount or 0.0),
                "attendance_count": today_report.attendance_count or 0,
                # New production template fields
                "gold": float(today_report.gold or 0.0),
                "diamond": float(today_report.diamond or 0.0),
                "platinum": float(today_report.platinum or 0.0),
                "silver": float(today_report.silver or 0.0),
                "gold_weight": today_report.gold_weight,
                "diamond_weight": today_report.diamond_weight,
                "platinum_weight": today_report.platinum_weight,
                "silver_weight": today_report.silver_weight,
                "silver_mrp": float(today_report.silver_mrp or 0.0),
                "total_revenue": float(today_report.total_revenue or 0.0),
                "digigold": today_report.digigold or 0,
                "digisilver": today_report.digisilver or 0,
                "digigold_enrollments": today_report.digigold_enrollments or 0,
                "digisilver_enrollments": today_report.digisilver_enrollments or 0,
                "employees_present": today_report.employees_present or 0,
                "employees_absent": today_report.employees_absent or 0,
                "customer_complaints": today_report.customer_complaints or "None",
                "operational_issues": today_report.operational_issues or "None",
                "remarks": today_report.remarks or "None"
            } if today_report else None
        }
    }

    print(f"[DASHBOARD LOG] /api/v1/branches/{branch_id}/analytics - Branch '{branch.name}', report_date={report_date}, target_date={target_date}, Reports in date range [{start} to {end}]: {len(reports)}, Today's emp performances: {len(employee_performances_list)}")

    return res_dict
