from typing import Optional
from pydantic import BaseModel, field_serializer
import uuid
from datetime import datetime

class NotificationBase(BaseModel):
    title: str
    message: str
    type: str
    category: str = "Updates"
    branch_id: Optional[uuid.UUID] = None

class NotificationCreate(NotificationBase):
    pass

class NotificationUpdate(BaseModel):
    is_read: bool

class NotificationInDB(NotificationBase):
    id: uuid.UUID
    user_id: uuid.UUID
    is_read: bool
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, dt: datetime, _info):
        from datetime import timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    class Config:
        from_attributes = True

