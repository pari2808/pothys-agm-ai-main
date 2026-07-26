import uuid
from typing import List, Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskUpdate

class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, task_id: uuid.UUID) -> Optional[Task]:
        """Fetch task by primary key UUID."""
        res = await self.db.execute(select(Task).where(Task.id == task_id))
        return res.scalars().first()

    async def get_all_tasks(self) -> Sequence[Task]:
        """Fetch all tasks in the system (ordered by due date)."""
        res = await self.db.execute(select(Task).order_by(Task.due_date.asc()))
        return res.scalars().all()

    async def get_all_assigned_to(self, user_id: uuid.UUID) -> Sequence[Task]:
        """Fetch tasks assigned to a specific manager."""
        res = await self.db.execute(
            select(Task)
            .where(Task.assigned_to == user_id)
            .order_by(Task.due_date.asc())
        )
        return res.scalars().all()

    async def create(self, assigned_by_id: uuid.UUID, task_in: TaskCreate) -> Task:
        """Create and persist a new task assignment."""
        db_task = Task(
            title=task_in.title,
            description=task_in.description,
            assigned_to=task_in.assigned_to,
            assigned_by=assigned_by_id,
            due_date=task_in.due_date,
            priority=task_in.priority.upper(),
            status="PENDING"
        )
        self.db.add(db_task)
        await self.db.commit()
        await self.db.refresh(db_task)
        return db_task

    async def update(self, db_task: Task, task_in: TaskUpdate) -> Task:
        """Update an existing task and save modifications."""
        update_data = task_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_task, field, value)
        
        await self.db.commit()
        await self.db.refresh(db_task)
        return db_task
