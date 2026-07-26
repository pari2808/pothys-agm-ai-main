import uuid
from typing import Optional
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[uuid.UUID] = None
    role: Optional[str] = None
    branch_id: Optional[uuid.UUID] = None
