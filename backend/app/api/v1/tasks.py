import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user, check_role
from app.models.user import User
from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter()

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["AGM"]))
):
    """Assign a new operational task to a branch manager. Only accessible by AGM."""
    task_repo = TaskRepository(db)
    
    # Verify manager exists
    from app.repositories.user import UserRepository
    user_repo = UserRepository(db)
    target_user = await user_repo.get_by_id(payload.assigned_to)
    if not target_user or target_user.role != "MANAGER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The assigned user must be a valid branch manager"
        )
        
    task = await task_repo.create(assigned_by_id=current_user.id, task_in=payload)
    return task

@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["AGM", "MANAGER"]))
):
    """
    List tasks.
    AGM receives a master list of all tasks; Managers receive only their assigned tasks.
    """
    task_repo = TaskRepository(db)
    if current_user.role == "AGM":
        tasks = await task_repo.get_all_tasks()
    else:
        tasks = await task_repo.get_all_assigned_to(current_user.id)
    return tasks

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task_by_id(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["AGM", "MANAGER"]))
):
    """Retrieve details of a task."""
    task_repo = TaskRepository(db)
    task = await task_repo.get_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
        
    # Check authorization for MANAGER
    if current_user.role == "MANAGER" and task.assigned_to != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this task"
        )
    return task

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_role(["AGM", "MANAGER"]))
):
    """
    Update a task.
    AGM can edit all parameters (assigned_to, priority, title, etc).
    Branch Managers can only update status and manager_remarks.
    """
    task_repo = TaskRepository(db)
    task = await task_repo.get_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    # Manager restriction
    if current_user.role == "MANAGER":
        if task.assigned_to != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to modify this task"
            )
        
        # Enforce that Manager can only edit status and remarks
        # Create a filtered TaskUpdate payload
        manager_payload = TaskUpdate(
            status=payload.status,
            manager_remarks=payload.manager_remarks
        )
        updated_task = await task_repo.update(task, manager_payload)
        return updated_task

    # AGM can update everything
    updated_task = await task_repo.update(task, payload)
    return updated_task
