import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.branch import Branch
from app.models.meeting import Meeting
from app.core.security import get_password_hash

@pytest.fixture
async def seed_meeting_data(db_session: AsyncSession):
    """Seed AGM and Manager accounts for meeting invitations and emails."""
    b1 = Branch(name="Padi Mahal", code="PADI", monthly_sales_target=500000)
    db_session.add(b1)
    await db_session.commit()
    await db_session.refresh(b1)

    mgr_pw = get_password_hash("managerPassword123")
    manager = User(
        email="padi@pothys.com",
        password_hash=mgr_pw,
        full_name="Padi Manager",
        role="MANAGER",
        branch_id=b1.id
    )

    agm_pw = get_password_hash("agmPassword123")
    agm = User(
        email="agm@pothys.com",
        password_hash=agm_pw,
        full_name="AGM Executive",
        role="AGM",
        branch_id=None
    )

    db_session.add_all([manager, agm])
    await db_session.commit()
    await db_session.refresh(manager)
    await db_session.refresh(agm)

    return {
        "manager": manager,
        "agm": agm
    }

async def get_jwt_token(client: TestClient, email: str, password: str) -> str:
    """Helper to get JWT token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    return response.json()["access_token"]

async def test_agm_schedule_meeting_success(client: TestClient, db_session: AsyncSession, seed_meeting_data):
    """AGM schedules a meeting and invites the manager."""
    token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    mgr_id = seed_meeting_data["manager"].id
    start = datetime.now() + timedelta(days=2)
    end = start + timedelta(hours=1)

    response = client.post(
        "/api/v1/meetings",
        headers=headers,
        json={
            "title": "Monthly Target Alignment",
            "agenda": "Review branch budgets and regional performance targets.",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "attendees": [str(mgr_id)]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Monthly Target Alignment"
    assert data["status"] == "SCHEDULED"
    assert len(data["attendees"]) == 1
    assert data["attendees"][0]["email"] == "padi@pothys.com"

    # Verify DB
    meet_id = uuid.UUID(data["id"])
    db_res = await db_session.execute(
        select(Meeting).where(Meeting.id == meet_id)
    )
    meeting = db_res.scalars().first()
    assert meeting is not None
    assert meeting.organizer_id == seed_meeting_data["agm"].id

async def test_manager_list_invited_meetings(client: TestClient, db_session: AsyncSession, seed_meeting_data):
    """Manager can view meetings they are invited to."""
    agm_id = seed_meeting_data["agm"].id
    mgr_id = seed_meeting_data["manager"].id
    
    start = datetime.now() + timedelta(days=1)
    end = start + timedelta(hours=1)

    # Seed meeting invitation
    m = Meeting(
        title="Weekly Sync",
        agenda="Sync",
        start_time=start,
        end_time=end,
        organizer_id=agm_id,
        status="SCHEDULED",
        attendees=[seed_meeting_data["manager"]]
    )
    db_session.add(m)
    await db_session.commit()

    token = await get_jwt_token(client, "padi@pothys.com", "managerPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/meetings", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Weekly Sync"

async def test_agm_write_notes_triggers_summary(client: TestClient, db_session: AsyncSession, seed_meeting_data):
    """AGM completes a meeting and saves notes, triggering AI summaries."""
    agm_id = seed_meeting_data["agm"].id
    m = Meeting(
        title="Inventory Review",
        agenda="Locker audit details.",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(hours=1),
        organizer_id=agm_id,
        status="SCHEDULED"
    )
    db_session.add(m)
    await db_session.commit()
    await db_session.refresh(m)

    token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch(
        f"/api/v1/meetings/{m.id}/notes",
        headers=headers,
        json={"notes": "All gold sets counted. Discovered 2 gold necklaces missing in storage."}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["notes"] == "All gold sets counted. Discovered 2 gold necklaces missing in storage."

async def test_email_generation_success(client: TestClient, seed_meeting_data):
    """AGM requests AI email generation for Pothys operations."""
    token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/emails/generate",
        headers=headers,
        json={
            "template_type": "TASK_REMINDER",
            "context": "Manager needs to upload Padi gold sales report for yesterday."
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "subject" in data
    assert "body" in data
    assert "Padi" in data["body"]

async def test_email_generation_blocked_out_of_domain(client: TestClient, seed_meeting_data):
    """Email assistant rejects prompts regarding out-of-domain topics (programming, recipes)."""
    token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/emails/generate",
        headers=headers,
        json={
            "template_type": "GENERAL_ANNOUNCEMENT",
            "context": "Tell me how to write a quicksort algorithm in python."
        }
    )
    assert response.status_code == 400
    assert "restricted to Pothys business operations" in response.json()["detail"]
