import pytest
import uuid
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.branch import Branch
from app.models.report import DailyReport
from app.core.security import get_password_hash

@pytest.fixture
async def seed_branch_data(db_session: AsyncSession):
    """Seed test branches, manager, and AGM accounts, plus daily reports."""
    b1 = Branch(name="Padi Swarna Mahal", code="PADI", monthly_sales_target=500000)
    b2 = Branch(name="Coimbatore Swarna Mahal", code="COIMBATORE", monthly_sales_target=400000)
    db_session.add_all([b1, b2])
    await db_session.commit()
    await db_session.refresh(b1)
    await db_session.refresh(b2)

    # Manager of Padi
    mgr_pw = get_password_hash("managerPassword123")
    manager = User(
        email="padi@pothys.com",
        password_hash=mgr_pw,
        full_name="Padi Manager",
        role="MANAGER",
        branch_id=b1.id
    )

    # Manager of Coimbatore
    manager_cbe = User(
        email="coimbatore@pothys.com",
        password_hash=mgr_pw,
        full_name="CBE Manager",
        role="MANAGER",
        branch_id=b2.id
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
    
    db_session.add_all([manager, manager_cbe, agm])
    await db_session.commit()
    await db_session.refresh(manager)
    await db_session.refresh(manager_cbe)
    await db_session.refresh(agm)

    # Create reports for b1 (Padi)
    today = date.today()
    r1 = DailyReport(
        branch_id=b1.id,
        manager_id=manager.id,
        date=today,
        sales_amount=450000.00,
        attendance_count=35,
        target_achievement=90.00,
        remarks="Excellent sales",
        issues=""
    )
    r2 = DailyReport(
        branch_id=b1.id,
        manager_id=manager.id,
        date=today - timedelta(days=1),
        sales_amount=400000.00,
        attendance_count=32,
        target_achievement=80.00,
        remarks="Moderate walkins",
        issues="Minor water leakage in lobby"
    )
    db_session.add_all([r1, r2])
    await db_session.commit()

    return {
        "branch_padi": b1,
        "branch_coimbatore": b2,
        "manager": manager,
        "manager_cbe": manager_cbe,
        "agm": agm,
        "report_today": r1,
        "report_yesterday": r2
    }

async def get_jwt_token(client: TestClient, email: str, password: str) -> str:
    """Helper to get JWT token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    return response.json()["access_token"]

async def test_list_branches_dashboard_success(client: TestClient, seed_branch_data):
    """AGM fetches dashboard branch list."""
    token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/branches", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Verify report status is mapped correctly
    padi_status = next(b for b in data if b["code"] == "PADI")
    cbe_status = next(b for b in data if b["code"] == "COIMBATORE")
    
    assert padi_status["status"] == "SUBMITTED"
    assert padi_status["report"]["sales_amount"] == 450000.00
    assert cbe_status["status"] == "PENDING"
    assert cbe_status["report"] is None

async def test_get_branch_analytics_agm(client: TestClient, seed_branch_data):
    """AGM accesses Coimbatore/Padi analytics."""
    token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    b1_id = seed_branch_data["branch_padi"].id
    response = client.get(f"/api/v1/branches/{b1_id}/analytics", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["branch"]["code"] == "PADI"
    assert data["summary"]["total_sales"] == 850000.00
    assert data["summary"]["average_attendance"] == 33.5
    assert len(data["recent_issues"]) == 1
    assert "leakage" in data["recent_issues"][0]["issues"]

async def test_get_branch_analytics_manager_own(client: TestClient, seed_branch_data):
    """Manager accesses their own branch's analytics."""
    token = await get_jwt_token(client, "padi@pothys.com", "managerPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    b1_id = seed_branch_data["branch_padi"].id
    response = client.get(f"/api/v1/branches/{b1_id}/analytics", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["branch"]["code"] == "PADI"

async def test_get_branch_analytics_manager_forbidden(client: TestClient, seed_branch_data):
    """Manager forbidden from accessing another branch's analytics."""
    token = await get_jwt_token(client, "padi@pothys.com", "managerPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    b2_id = seed_branch_data["branch_coimbatore"].id
    response = client.get(f"/api/v1/branches/{b2_id}/analytics", headers=headers)
    assert response.status_code == 403
    assert "only authorized to access analytics" in response.json()["detail"]
