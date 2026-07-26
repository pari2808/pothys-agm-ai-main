import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: str = Field(description="Must be 'AGM' or 'MANAGER'")
    branch_id: Optional[uuid.UUID] = None

class UserCreate(UserBase):
    password: str = Field(min_length=6)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None

class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime
    branch_name: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            uuid.UUID: str
        }
