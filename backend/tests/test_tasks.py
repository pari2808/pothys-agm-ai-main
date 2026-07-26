import pytest
import uuid
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.branch import Branch
from app.models.task import Task
from app.core.security import get_password_hash

@pytest.fixture
async def seed_task_data(db_session: AsyncSession):
    """Seed test data with AGM, Managers, and a branch."""
    b1 = Branch(name="Padi Mahal", code="PADI", monthly_sales_target=500000)
    db_session.add(b1)
    await db_session.flush()

    # Manager 1
    mgr_pw = get_password_hash("managerPassword123")
    manager1 = User(
        email="padi@pothys.com",
        password_hash=mgr_pw,
        full_name="Padi Manager",
        role="MANAGER",
        branch_id=b1.id
    )

    # Manager 2 (Another branch)
    manager2 = User(
        email="coimbatore@pothys.com",
        password_hash=mgr_pw,
        full_name="Coimbatore Manager",
        role="MANAGER",
        branch_id=None
    )

    # AGM
    agm_pw = get_password_hash("agmPassword123")
    agm = User(
        email="agm@pothys.com",
        password_hash=agm_pw,
        full_name="AGM Executive",
        role="AGM",
        branch_id=None
    )

    db_session.add_all([manager1, manager2, agm])
    await db_session.flush()
    await db_session.refresh(manager1)
    await db_session.refresh(manager2)
    await db_session.refresh(agm)

    return {
        "branch": b1,
        "manager1": manager1,
        "manager2": manager2,
        "agm": agm
    }

async def get_jwt_token(client: TestClient, email: str, password: str) -> str:
    """Helper to get JWT token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    return response.json()["access_token"]

async def test_agm_assign_task_success(client: TestClient, db_session: AsyncSession, seed_task_data):
    """AGM assigns a task to a manager successfully."""
    token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    mgr1_id = seed_task_data["manager1"].id
    response = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={
            "title": "Audit Gold Inventory",
            "description": "Please count and verify stock in locker A.",
            "assigned_to": str(mgr1_id),
            "due_date": "2026-07-20",
            "priority": "HIGH"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Audit Gold Inventory"
    assert data["status"] == "PENDING"
    assert data["priority"] == "HIGH"
    
    # Verify DB
    task_id = uuid.UUID(data["id"])
    db_res = await db_session.execute(select(Task).where(Task.id == task_id))
    task = db_res.scalars().first()
    assert task is not None
    assert task.assigned_to == mgr1_id
    assert task.assigned_by == seed_task_data["agm"].id

async def test_manager_list_own_tasks(client: TestClient, db_session: AsyncSession, seed_task_data):
    """Managers can see tasks assigned to them, but not others."""
    # Seed 2 tasks (one to mgr1, one to mgr2)
    agm_id = seed_task_data["agm"].id
    mgr1_id = seed_task_data["manager1"].id
    mgr2_id = seed_task_data["manager2"].id

    t1 = Task(
        title="Task for Padi",
        description="",
        assigned_to=mgr1_id,
        assigned_by=agm_id,
        due_date=date(2026, 7, 20),
        priority="LOW"
    )
    t2 = Task(
        title="Task for CBE",
        description="",
        assigned_to=mgr2_id,
        assigned_by=agm_id,
        due_date=date(2026, 7, 20),
        priority="HIGH"
    )
    db_session.add_all([t1, t2])
    await db_session.commit()

    # Log in as Manager 1
    token = await get_jwt_token(client, "padi@pothys.com", "managerPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/tasks", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Task for Padi"

async def test_manager_update_status_and_remarks_only(client: TestClient, db_session: AsyncSession, seed_task_data):
    """Manager can update status and remarks, but changes to core fields are ignored/blocked."""
    agm_id = seed_task_data["agm"].id
    mgr1_id = seed_task_data["manager1"].id

    t = Task(
        title="Audit Locker B",
        description="Verify raw weights.",
        assigned_to=mgr1_id,
        assigned_by=agm_id,
        due_date=date(2026, 7, 20),
        priority="MEDIUM",
        status="PENDING"
    )
    db_session.add(t)
    await db_session.commit()
    await db_session.refresh(t)

    # Log in as Manager 1
    token = await get_jwt_token(client, "padi@pothys.com", "managerPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to change status/remarks AND priority/title
    response = client.patch(
        f"/api/v1/tasks/{t.id}",
        headers=headers,
        json={
            "title": "Hack Task Name",
            "priority": "LOW",
            "status": "IN_PROGRESS",
            "manager_remarks": "Locker count started."
        }
    )
    assert response.status_code == 200
    data = response.json()
    
    # Status and remarks should change, but title and priority must remain unchanged!
    assert data["status"] == "IN_PROGRESS"
    assert data["manager_remarks"] == "Locker count started."
    assert data["title"] == "Audit Locker B"
    assert data["priority"] == "MEDIUM"
