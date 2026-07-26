import uuid
from typing import List, Optional, Sequence
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import AIConversation, AIMessage

class ConversationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_conversation(self, conversation_id: uuid.UUID) -> Optional[AIConversation]:
        """Fetch a conversation thread along with its messages preloaded."""
        stmt = (
            select(AIConversation)
            .where(AIConversation.id == conversation_id)
            .options(selectinload(AIConversation.messages))
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_user_conversations(self, user_id: uuid.UUID) -> Sequence[AIConversation]:
        """List all conversation threads initiated by a specific user, sorted by date descending."""
        stmt = (
            select(AIConversation)
            .where(AIConversation.user_id == user_id)
            .order_by(AIConversation.created_at.desc())
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def create_conversation(self, user_id: uuid.UUID, title: str) -> AIConversation:
        """Initialize a new chat conversation thread."""
        conversation = AIConversation(
            user_id=user_id,
            title=title
        )
        self.db.add(conversation)
        await self.db.commit()
        await self.db.refresh(conversation)
        return conversation

    async def create_message(
        self,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        retrieved_sources: Optional[List[str]] = None
    ) -> AIMessage:
        """Append a new user or assistant message to a conversation thread."""
        message = AIMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            retrieved_sources=retrieved_sources or []
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message
