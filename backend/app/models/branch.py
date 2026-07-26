import uuid
from sqlalchemy import String, Numeric, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    monthly_sales_target: Mapped[float] = mapped_column(Numeric(15, 2), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="branch")
    reports: Mapped[list["DailyReport"]] = relationship(back_populates="branch")
    documents: Mapped[list["Document"]] = relationship(back_populates="branch")
