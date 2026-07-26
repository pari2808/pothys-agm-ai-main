import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class AIQueryRequest(BaseModel):
    conversation_id: Optional[uuid.UUID] = None
    content: str

class AIMessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID          # returned so frontend can persist the thread
    role: str  # "user" or "assistant"
    content: str
    retrieved_sources: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AIConversationResponse(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime

    class Config:
        from_attributes = True

class AIConversationDetailResponse(AIConversationResponse):
    messages: List[AIMessageResponse]
