import uuid
from sqlalchemy import String, ForeignKey, DateTime, func, Text, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base

# Association table for meeting attendees (many-to-many)
meeting_attendees = Table(
    "meeting_attendees",
    Base.metadata,
    Column("meeting_id", ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)

class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    agenda: Mapped[str] = mapped_column(Text, nullable=True)
    start_time: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    organizer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED")  # "SCHEDULED", "COMPLETED", "CANCELLED"
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    organizer: Mapped["User"] = relationship(back_populates="organized_meetings")
    attendees: Mapped[list["User"]] = relationship(secondary=meeting_attendees)
    document_chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="meeting")
