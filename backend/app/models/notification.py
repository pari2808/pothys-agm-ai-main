import uuid
from typing import Optional
from sqlalchemy import String, ForeignKey, DateTime, func, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # "Report Submitted", "Report Pending", etc.
    category: Mapped[str] = mapped_column(String(50), default="Updates", nullable=False)  # "Updates", "Action Required"
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    branch_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("branches.id"), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="notifications")
