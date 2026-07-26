from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, desc, func

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationInDB

router = APIRouter()

async def sync_user_notifications(db: AsyncSession, current_user: User):
    """
    Synchronizes notifications table with today's branch activity and seeds alerts.
    Assigns category ('Updates' vs 'Action Required') to every notification.
    """
    from datetime import date, datetime, timedelta, timezone, time
    from app.models.branch import Branch
    from app.models.report import DailyReport
    from app.core.config import settings
    
    # Parse configured submission limit time (e.g. "19:00" IST)
    try:
        limit_hour, limit_minute = map(int, settings.REPORT_SUBMISSION_TIME.split(":"))
    except Exception:
        limit_hour, limit_minute = 19, 0
        
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    limit_time = time(limit_hour, limit_minute)
    is_after_limit = now_ist.time() >= limit_time
    
    target_date = date.today()
    
    # 1. Fetch branches and daily reports for today
    branches_res = await db.execute(select(Branch))
    branches = branches_res.scalars().all()
    
    reports_res = await db.execute(
        select(DailyReport).where(DailyReport.date == target_date)
    )
    reports = reports_res.scalars().all()
    reports_map = {r.branch_id: r for r in reports}
    
    # Get short branch name helper
    def get_short_branch_name(name: str) -> str:
        return name.replace("Swarna Mahal", "").strip()
        
    # Get existing notifications for this user
    existing_res = await db.execute(
        select(Notification).where(Notification.user_id == current_user.id)
    )
    existing_notifications = existing_res.scalars().all()
    existing_by_title = {n.title: n for n in existing_notifications}
    
    # Synchronize today's notifications
    for branch in branches:
        short_name = get_short_branch_name(branch.name)
        pending_title = f"Report Pending: {short_name}"
        submitted_title = f"Report Submitted: {short_name}"
        issue_title = f"Operational Issue at {short_name}"
        
        # If report has been submitted
        if branch.id in reports_map:
            report = reports_map[branch.id]
            
            # If "Report Pending" notification exists, remove it
            if pending_title in existing_by_title:
                await db.delete(existing_by_title[pending_title])
                
            # Operational Issue (if any)
            if report.issues and report.issues.strip() and report.issues.lower() != "none":
                if issue_title not in existing_by_title:
                    new_notif = Notification(
                        user_id=current_user.id,
                        title=issue_title,
                        message=report.issues.strip(),
                        type="Operational Issue",
                        category="Action Required",
                        is_read=False,
                        branch_id=branch.id,
                        created_at=datetime.now(timezone.utc) - timedelta(minutes=30)
                    )
                    db.add(new_notif)
            else:
                if issue_title in existing_by_title:
                    await db.delete(existing_by_title[issue_title])
        else:
            # Report is pending/missing for today.
            # Ensure "Report Submitted" and "Operational Issue" notifications for today are removed
            if submitted_title in existing_by_title:
                await db.delete(existing_by_title[submitted_title])
            if issue_title in existing_by_title:
                await db.delete(existing_by_title[issue_title])
                
            # Check if it is past the configured limit time
            if is_after_limit:
                # Create "Report Pending" notification if not exists
                if pending_title not in existing_by_title:
                    pending_datetime_ist = now_ist.replace(hour=limit_hour, minute=limit_minute, second=0, microsecond=0)
                    pending_datetime_utc = pending_datetime_ist.astimezone(timezone.utc)
                    
                    new_notif = Notification(
                        user_id=current_user.id,
                        title=pending_title,
                        message=f"{branch.name} has not submitted today's report. Action required.",
                        type="Report Pending",
                        category="Action Required",
                        is_read=False,
                        branch_id=branch.id,
                        created_at=pending_datetime_utc
                    )
                    db.add(new_notif)
            else:
                # If before limit time, ensure "Report Pending" does not exist
                if pending_title in existing_by_title:
                    await db.delete(existing_by_title[pending_title])
                
    # Calculate Dashboard Aggregations for today's notifications
    total_rev = sum(r.total_revenue if r.total_revenue else r.sales_amount for r in reports)
    emp_absent = sum(r.employees_absent for r in reports if r.employees_absent)
    
    # Top Performing Branch
    top_branch_name = "N/A"
    top_branch_id = None
    max_rev = -1.0
    branch_map = {b.id: b for b in branches}
    for r in reports:
        rev = r.total_revenue if r.total_revenue else r.sales_amount
        if rev > max_rev:
            max_rev = rev
            if r.branch_id in branch_map:
                top_branch_name = get_short_branch_name(branch_map[r.branch_id].name)
                top_branch_id = r.branch_id
                
    # Top Performing Employee
    from app.models.employee import Employee
    from app.models.employee_performance import EmployeePerformance
    
    stmt = (
        select(EmployeePerformance, Employee, Branch)
        .join(Employee, EmployeePerformance.employee_id == Employee.id)
        .join(DailyReport, EmployeePerformance.report_id == DailyReport.id)
        .join(Branch, Employee.branch_id == Branch.id)
        .where(DailyReport.date == target_date)
        .order_by((EmployeePerformance.gold_amount + EmployeePerformance.silver_amount + EmployeePerformance.platinum_amount + EmployeePerformance.diamond_amount).desc())
        .limit(1)
    )
    top_perf_res = await db.execute(stmt)
    top_perf = top_perf_res.first()
    top_employee_branch_id = None
    if top_perf:
        perf, emp, b_obj = top_perf
        total_emp_sales = float(perf.gold_amount + perf.silver_amount + perf.platinum_amount + perf.diamond_amount)
        top_employee_str = f"{emp.name} ({get_short_branch_name(b_obj.name)}) - Rs. {total_emp_sales:,.2f}"
        top_employee_branch_id = b_obj.id
    else:
        top_employee_str = "N/A"
        
    # Attendance Alert
    if emp_absent > 0:
        att_title = "Attendance Alert"
        if att_title not in existing_by_title:
            new_notif = Notification(
                user_id=current_user.id,
                title=att_title,
                message=f"{emp_absent} employee(s) absent today across all branches. Check rosters.",
                type="Attendance Alert",
                is_read=False,
                created_at=datetime.now(timezone.utc) - timedelta(hours=5)
            )
            db.add(new_notif)
    else:
        if "Attendance Alert" in existing_by_title:
            await db.delete(existing_by_title["Attendance Alert"])
            
    # Customer Complaints
    complaints = []
    for r in reports:
        if r.customer_complaints and r.customer_complaints.lower() != "none" and r.customer_complaints.strip():
            complaints.append((r.branch_id, r.customer_complaints.strip()))
            
    for idx, (b_id, comp) in enumerate(complaints, start=1):
        comp_title = f"High Customer Complaints #{idx}"
        if comp_title not in existing_by_title:
            new_notif = Notification(
                user_id=current_user.id,
                title=comp_title,
                message=f'Customer reported: "{comp}"',
                type="Customer Complaint",
                category="Action Required",
                is_read=False,
                branch_id=b_id,
                created_at=datetime.now(timezone.utc) - timedelta(hours=3)
            )
            db.add(new_notif)
            
    # Top Branch
    if top_branch_name != "N/A":
        top_b_title = "Highest Performing Branch"
        if top_b_title not in existing_by_title:
            new_notif = Notification(
                user_id=current_user.id,
                title=top_b_title,
                message=f"{top_branch_name} is leading in sales and revenue growth today.",
                type="Highest Performing Branch",
                is_read=False,
                branch_id=top_branch_id,
                created_at=datetime.now(timezone.utc) - timedelta(hours=2)
            )
            db.add(new_notif)
            
    # Top Employee
    if top_employee_str != "N/A":
        top_e_title = "Highest Performing Executive"
        if top_e_title not in existing_by_title:
            new_notif = Notification(
                user_id=current_user.id,
                title=top_e_title,
                message=f"{top_employee_str} achieved outstanding operations score today.",
                type="Highest Performing Executive",
                is_read=False,
                branch_id=top_employee_branch_id,
                created_at=datetime.now(timezone.utc) - timedelta(hours=1.5)
            )
            db.add(new_notif)
            
    # AI Recommendation (Removed per user request)
    ai_title = "AI RAG Insight"
    if ai_title in existing_by_title:
        await db.delete(existing_by_title[ai_title])
        
    await db.commit()

@router.get("/unread-count", response_model=dict)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lightweight endpoint returning the unread notification count for bell badge."""
    await sync_user_notifications(db, current_user)
    result = await db.execute(
        select(func.count(Notification.id))
        .where(Notification.user_id == current_user.id)
        .where(Notification.is_read == False)
    )
    count = result.scalar() or 0
    return {"count": count, "unread_count": count}

@router.get("", response_model=List[NotificationInDB])
@router.get("/", response_model=List[NotificationInDB])
async def get_notifications(
    category: Optional[str] = Query(None, description="Filter category: 'Updates', 'Action Required', or None for all"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of notifications for the current user, newest first.
    Optionally filter by category.
    """
    await sync_user_notifications(db, current_user)
    
    query = select(Notification).where(Notification.user_id == current_user.id)
    
    if category and category.lower() != "all":
        # Handle category matching
        if category.lower().replace(" ", "_") in ["action_required", "actionrequired", "action required"]:
            query = query.where(Notification.category == "Action Required")
        elif category.lower() == "updates":
            query = query.where(Notification.category == "Updates")
            
    query = query.order_by(desc(Notification.created_at))
    
    result = await db.execute(query)
    return result.scalars().all()

@router.put("/{notification_id}/read", response_model=NotificationInDB)
@router.patch("/{notification_id}/read", response_model=NotificationInDB)
async def mark_as_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a single notification as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalars().first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return notification

@router.post("/mark-all-read", response_model=dict)
@router.put("/read-all", response_model=dict)
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark all unread notifications for the current user as read."""
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id)
        .where(Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {"status": "success", "message": "All notifications marked as read"}

@router.delete("/clear-all", response_model=dict)
@router.delete("", response_model=dict)
@router.delete("/", response_model=dict)
async def clear_all_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Completely delete all notification history for the current user from the database."""
    await db.execute(
        delete(Notification).where(Notification.user_id == current_user.id)
    )
    await db.commit()
    return {"status": "success", "message": "All notification history deleted permanently"}

@router.delete("/{notification_id}", response_model=dict)
async def delete_single_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a single notification from the database."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id
        )
    )
    notification = result.scalars().first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    await db.delete(notification)
    await db.commit()
    return {"status": "success", "message": "Notification deleted permanently"}
