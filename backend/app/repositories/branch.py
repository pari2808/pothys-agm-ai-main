import uuid
from typing import Optional, Sequence
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.branch import Branch
from app.schemas.branch import BranchCreate

class BranchRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, branch_id: uuid.UUID) -> Optional[Branch]:
        """Fetch branch by primary key UUID."""
        result = await self.db.execute(select(Branch).where(Branch.id == branch_id))
        return result.scalars().first()

    async def get_by_code(self, code: str) -> Optional[Branch]:
        """Fetch branch by unique branch code."""
        result = await self.db.execute(select(Branch).where(Branch.code == code))
        return result.scalars().first()

    async def get_all(self) -> Sequence[Branch]:
        """Fetch list of all 8 branches."""
        result = await self.db.execute(select(Branch).order_by(Branch.name))
        return result.scalars().all()

    async def create(self, branch_in: BranchCreate) -> Branch:
        """Create new branch instance."""
        db_branch = Branch(
            name=branch_in.name,
            code=branch_in.code.upper(),
            monthly_sales_target=branch_in.monthly_sales_target
        )
        self.db.add(db_branch)
        await self.db.commit()
        await self.db.refresh(db_branch)
        return db_branch
