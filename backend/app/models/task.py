import uuid
from datetime import date
from sqlalchemy import String, ForeignKey, DateTime, func, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assigned_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")  # "LOW", "MEDIUM", "HIGH"
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)  # "PENDING", "IN_PROGRESS", "COMPLETED"
    manager_remarks: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    assigned_to_user: Mapped["User"] = relationship(
        back_populates="tasks_assigned_to", foreign_keys=[assigned_to]
    )
    assigned_by_user: Mapped["User"] = relationship(
        back_populates="tasks_assigned_by", foreign_keys=[assigned_by]
    )
