import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas.user import UserResponse

class MeetingCreate(BaseModel):
    title: str = Field(..., max_length=200)
    agenda: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: List[uuid.UUID] = []  # List of user IDs

class MeetingNotesUpdate(BaseModel):
    notes: str

class MeetingResponse(BaseModel):
    id: uuid.UUID
    title: str
    agenda: Optional[str]
    start_time: datetime
    end_time: datetime
    organizer_id: uuid.UUID
    status: str  # "SCHEDULED", "COMPLETED", "CANCELLED"
    notes: Optional[str]
    ai_summary: Optional[str]
    created_at: datetime
    attendees: List[UserResponse] = []

    class Config:
        from_attributes = True
