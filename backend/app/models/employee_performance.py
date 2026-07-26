import uuid
from sqlalchemy import Numeric, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class EmployeePerformance(Base):
    __tablename__ = "employee_performances"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    
    # New production template columns
    gold: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    diamond: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    platinum: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    silver: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    silver_mrp: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    subhiksham_count: Mapped[int] = mapped_column(Integer, default=0)
    subhiksham_value: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    viruksham_count: Mapped[int] = mapped_column(Integer, default=0)
    viruksham_value: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    digigold: Mapped[int] = mapped_column(Integer, default=0)
    digisilver: Mapped[int] = mapped_column(Integer, default=0)
    # Additional fields from dc721e0 branch
    gold_grams_sold: Mapped[float] = mapped_column(Numeric(10, 3), default=0.0)
    gold_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    silver_grams_sold: Mapped[float] = mapped_column(Numeric(10, 3), default=0.0)
    silver_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    platinum_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    diamond_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    digigold_enrollments: Mapped[int] = mapped_column(Integer, default=0)
    digisilver_enrollments: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    report: Mapped["DailyReport"] = relationship(back_populates="employee_performances")
    employee: Mapped["Employee"] = relationship(back_populates="performances")
