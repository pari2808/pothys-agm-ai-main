import uuid
from typing import Optional
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models import User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash

class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Fetch user by primary key UUID."""
        result = await self.db.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.branch))
        )
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by email using case-insensitive match."""
        result = await self.db.execute(
            select(User)
            .where(func.lower(User.email) == email.lower())
            .options(selectinload(User.branch))
        )
        return result.scalars().first()

    async def create(self, user_in: UserCreate) -> User:
        """Create new user with encrypted password hash."""
        db_user = User(
            email=user_in.email.lower(),
            password_hash=get_password_hash(user_in.password),
            full_name=user_in.full_name,
            role=user_in.role,
            branch_id=user_in.branch_id
        )
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        return db_user

    async def check_agm_exists(self) -> bool:
        """Check if at least one user with AGM role exists."""
        result = await self.db.execute(select(User).where(User.role == "AGM"))
        return result.scalars().first() is not None

    async def get_by_reset_token(self, token: str) -> Optional[User]:
        """Fetch user by reset token match."""
        result = await self.db.execute(select(User).where(User.reset_token == token))
        return result.scalars().first()
