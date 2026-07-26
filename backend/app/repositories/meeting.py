import uuid
from typing import List, Optional, Sequence
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.meeting import Meeting, meeting_attendees
from app.models.user import User
from app.schemas.meeting import MeetingCreate

class MeetingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, meeting_id: uuid.UUID) -> Optional[Meeting]:
        """Fetch meeting by UUID with attendees details preloaded."""
        stmt = (
            select(Meeting)
            .where(Meeting.id == meeting_id)
            .options(selectinload(Meeting.attendees))
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_user_meetings(self, user_id: uuid.UUID) -> Sequence[Meeting]:
        """Fetch all meetings organized by or attended by a specific user."""
        # Find meetings where user_id is the organizer OR user_id is in the attendees table
        stmt = (
            select(Meeting)
            .outerjoin(Meeting.attendees)
            .where(
                or_(
                    Meeting.organizer_id == user_id,
                    User.id == user_id
                )
            )
            .options(selectinload(Meeting.attendees))
            .distinct()
            .order_by(Meeting.start_time.desc())
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def create(self, organizer_id: uuid.UUID, meeting_in: MeetingCreate) -> Meeting:
        """Create a new meeting schedule and associate invited attendees."""
        # Fetch attendees entities
        attendee_users = []
        if meeting_in.attendees:
            res = await self.db.execute(select(User).where(User.id.in_(meeting_in.attendees)))
            attendee_users = list(res.scalars().all())

        db_meeting = Meeting(
            title=meeting_in.title,
            agenda=meeting_in.agenda,
            start_time=meeting_in.start_time,
            end_time=meeting_in.end_time,
            organizer_id=organizer_id,
            status="SCHEDULED",
            notes="",
            ai_summary="",
            attendees=attendee_users
        )
        self.db.add(db_meeting)
        await self.db.commit()
        await self.db.refresh(db_meeting)
        return db_meeting

    async def update_notes_and_summary(self, meeting: Meeting, notes: str, ai_summary: str) -> Meeting:
        """Update meeting notes, mark as completed, and save the AI-generated summary."""
        meeting.notes = notes
        meeting.ai_summary = ai_summary
        meeting.status = "COMPLETED"
        await self.db.commit()
        await self.db.refresh(meeting)
        return meeting
