import uuid
from datetime import date
from typing import Optional, Sequence
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.report import DailyReport
from app.schemas.report import DailyReportCreate

class DailyReportRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, report_id: uuid.UUID) -> Optional[DailyReport]:
        """Fetch daily report by primary key ID."""
        result = await self.db.execute(select(DailyReport).where(DailyReport.id == report_id))
        return result.scalars().first()

    async def get_by_branch_and_date(self, branch_id: uuid.UUID, report_date: date) -> Optional[DailyReport]:
        """Fetch daily report for a specific branch on a given date."""
        result = await self.db.execute(
            select(DailyReport).where(
                and_(
                    DailyReport.branch_id == branch_id,
                    DailyReport.date == report_date
                )
            )
        )
        return result.scalars().first()

    async def get_all_by_branch(self, branch_id: uuid.UUID) -> Sequence[DailyReport]:
        """Fetch all daily reports uploaded for a specific branch, sorted by date descending."""
        result = await self.db.execute(
            select(DailyReport)
            .where(DailyReport.branch_id == branch_id)
            .order_by(DailyReport.date.desc())
        )
        return result.scalars().all()

    async def create(self, branch_id: uuid.UUID, manager_id: uuid.UUID, report_in: DailyReportCreate) -> DailyReport:
        """Insert a new daily report into the database."""
        from datetime import datetime, timezone
        db_report = DailyReport(
            branch_id=branch_id,
            manager_id=manager_id,
            date=report_in.date,
            sales_amount=report_in.sales_amount,
            attendance_count=report_in.attendance_count,
            target_achievement=report_in.target_achievement,
            inventory_status=report_in.inventory_status,
            remarks=report_in.remarks,
            original_file_url=report_in.original_file_url,
            status="SUBMITTED",
            uploaded_at=datetime.now(timezone.utc)
        )
        self.db.add(db_report)
        await self.db.commit()
        await self.db.refresh(db_report)
        return db_report

    async def get_reports_for_date(self, report_date: date) -> Sequence[DailyReport]:
        """Get reports from all branches for a specific date."""
        result = await self.db.execute(
            select(DailyReport)
            .where(DailyReport.date == report_date)
            .order_by(DailyReport.sales_amount.desc())
        )
        return result.scalars().all()

    async def get_date_range_metrics(self, start_date: date, end_date: date) -> Sequence[DailyReport]:
        """Get reports for all branches over a specific range of dates."""
        result = await self.db.execute(
            select(DailyReport)
            .where(and_(DailyReport.date >= start_date, DailyReport.date <= end_date))
            .order_by(DailyReport.date.desc())
        )
        return result.scalars().all()
