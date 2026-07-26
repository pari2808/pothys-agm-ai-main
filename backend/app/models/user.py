import uuid
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, func, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "AGM" or "MANAGER"
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("branches.id"), nullable=True)
    reset_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reset_token_expires: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    branch: Mapped["Branch"] = relationship(back_populates="users")

    @property
    def branch_name(self) -> Optional[str]:
        if "branch" in self.__dict__ and self.branch is not None:
            return self.branch.name
        return None

    uploaded_reports: Mapped[list["DailyReport"]] = relationship(back_populates="manager")
    uploaded_documents: Mapped[list["Document"]] = relationship(back_populates="uploader")
    tasks_assigned_to: Mapped[list["Task"]] = relationship(
        back_populates="assigned_to_user", foreign_keys="[Task.assigned_to]"
    )
    tasks_assigned_by: Mapped[list["Task"]] = relationship(
        back_populates="assigned_by_user", foreign_keys="[Task.assigned_by]"
    )
    organized_meetings: Mapped[list["Meeting"]] = relationship(back_populates="organizer")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")
    conversations: Mapped[list["AIConversation"]] = relationship(back_populates="user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
