import uuid
from datetime import date
from sqlalchemy import String, Numeric, Integer, Date, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class DailyReport(Base):
    __tablename__ = "daily_reports"
    __table_args__ = (UniqueConstraint('branch_id', 'date', name='uq_branch_date'),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), nullable=False)
    manager_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sales_amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    attendance_count: Mapped[int] = mapped_column(Integer, nullable=False)
    target_achievement: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)  # Percentage achieved
    inventory_status: Mapped[str] = mapped_column(String(500), nullable=True)
    remarks: Mapped[str] = mapped_column(String(1000), nullable=True)
    issues: Mapped[str] = mapped_column(String(1000), nullable=True)
    original_file_url: Mapped[str] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    uploaded_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Manager info
    sub_manager_name: Mapped[str] = mapped_column(String(100), nullable=True)

    # Branch-level aggregated values from production template
    gold: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    diamond: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    platinum: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    silver: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    silver_mrp: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    total_revenue: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    digigold: Mapped[int] = mapped_column(Integer, default=0)
    digisilver: Mapped[int] = mapped_column(Integer, default=0)

    # Additional Sheet 1 summary fields
    gold_sales: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    silver_sales: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    platinum_sales: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    diamond_sales: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)

    # Official Excel template consolidated weight/volume fields
    gold_weight: Mapped[str] = mapped_column(String(100), nullable=True)
    diamond_weight: Mapped[str] = mapped_column(String(100), nullable=True)
    platinum_weight: Mapped[str] = mapped_column(String(100), nullable=True)
    silver_weight: Mapped[str] = mapped_column(String(100), nullable=True)

    digigold_enrollments: Mapped[int] = mapped_column(Integer, default=0)
    digisilver_enrollments: Mapped[int] = mapped_column(Integer, default=0)

    # HR
    employees_present: Mapped[int] = mapped_column(Integer, default=0)
    employees_absent: Mapped[int] = mapped_column(Integer, default=0)
    customer_complaints: Mapped[str] = mapped_column(String(1000), nullable=True)
    operational_issues: Mapped[str] = mapped_column(String(1000), nullable=True)

    # Relationships
    branch: Mapped["Branch"] = relationship(back_populates="reports")
    manager: Mapped["User"] = relationship(back_populates="uploaded_reports")
    documents: Mapped[list["Document"]] = relationship(back_populates="report")
    document_chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="report")
    
    # New Sheet relationships
    employee_performances: Mapped[list["EmployeePerformance"]] = relationship(back_populates="report", cascade="all, delete-orphan")
    scheme_summary: Mapped["SchemeSummary"] = relationship(back_populates="report", uselist=False, cascade="all, delete-orphan")
