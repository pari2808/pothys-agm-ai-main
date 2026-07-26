import uuid
from sqlalchemy import Integer, Numeric, String, JSON, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class SchemeSummary(Base):
    __tablename__ = "scheme_summaries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("daily_reports.id", ondelete="CASCADE"), nullable=False)
    
    # Subhiksham & Viruksham scheme data (aggregated from employee rows)
    subhiksham_count: Mapped[int] = mapped_column(Integer, default=0)
    subhiksham_value: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    viruksham_count: Mapped[int] = mapped_column(Integer, default=0)
    viruksham_value: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    # Additional fields from dc721e0 branch
    digigold_total: Mapped[int] = mapped_column(Integer, default=0)
    digisilver_total: Mapped[int] = mapped_column(Integer, default=0)
    digigold_revenue: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)
    digisilver_revenue: Mapped[float] = mapped_column(Numeric(15, 2), default=0.0)

    # Retain scheme_items JSON for any additional scheme data
    scheme_items: Mapped[dict] = mapped_column(JSON, nullable=True)
    overall_remarks: Mapped[str] = mapped_column(String(1000), nullable=True)
    
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    report: Mapped["DailyReport"] = relationship(back_populates="scheme_summary")
