import uuid
import pytest
from unittest.mock import patch
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User
from app.models.branch import Branch
from app.models.report import DailyReport
from app.models.notification import Notification
from app.core.security import get_password_hash

@pytest.fixture
async def seed_data(db_session: AsyncSession):
    """Seed test branches, manager, and AGM accounts."""
    # Branches
    b1 = Branch(name="Padi Mahal", code="PADI", monthly_sales_target=500000)
    b2 = Branch(name="Coimbatore Mahal", code="COIMBATORE", monthly_sales_target=400000)
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

    # AGM
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
        "branch_padi": b1,
        "branch_coimbatore": b2,
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

async def test_upload_report_success_manual_metrics(client: TestClient, db_session: AsyncSession, seed_data):
    """Test standard report upload with manually filled fields."""
    token = await get_jwt_token(client, "padi@pothys.com", "managerPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/reports/upload",
        headers=headers,
        data={
            "report_date": "2026-07-16",
            "sales_amount": 450000.0,
            "attendance_count": 42,
            "target_achievement": 90.0,
            "inventory_status": "Gold inventory is stable.",
            "remarks": "Strong evening walk-ins.",
            "issues": "No major issues."
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["sales_amount"] == 450000.0
    assert data["attendance_count"] == 42
    assert data["target_achievement"] == 90.0
    assert data["remarks"] == "Strong evening walk-ins."

    # Verify database record exists
    report_id = data["id"]
    db_res = await db_session.execute(select(DailyReport).where(DailyReport.id == uuid.UUID(report_id)))
    report = db_res.scalars().first()
    assert report is not None
    assert report.sales_amount == 450000.0
    assert report.branch_id == seed_data["branch_padi"].id

async def test_upload_report_parsing_heuristics(client: TestClient, db_session: AsyncSession, seed_data):
    """Test report upload where metrics are missing in Form but parsed from file contents."""
    token = await get_jwt_token(client, "padi@pothys.com", "managerPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    # Patch parser and storage services to avoid physical file dependencies and third-party parsing failures
    mock_extracted_text = "Sales: Rs. 380,000\nAttendance: 35\nTarget Achievement: 85%"
    
    with patch("app.services.storage.storage_service.upload_file", return_value="/uploads/mock_file.pdf") as mock_upload, \
         patch("app.services.doc_parser.DocumentParser.extract_text_from_pdf", return_value=mock_extracted_text) as mock_pdf_extract:
        
        response = client.post(
            "/api/v1/reports/upload",
            headers=headers,
            data={
                "report_date": "2026-07-15",
                # Omit sales, attendance, and target to let the parser extract them
            },
            files={"file": ("report.pdf", b"dummy contents", "application/pdf")}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["sales_amount"] == 380000.0
        assert data["attendance_count"] == 35
        assert data["target_achievement"] == 85.0
        assert data["original_file_url"] == "/uploads/mock_file.pdf"
        
        mock_upload.assert_called_once()
        mock_pdf_extract.assert_called_once()

async def test_upload_report_unauthorized_for_agm(client: TestClient, seed_data):
    """Only Managers are authorized to upload operational reports."""
    token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/reports/upload",
        headers=headers,
        data={
            "report_date": "2026-07-16",
            "sales_amount": 10000,
            "attendance_count": 5,
            "target_achievement": 50
        }
    )
    assert response.status_code == 403
    assert "not have enough privileges" in response.json()["detail"]

async def test_get_pending_reports(client: TestClient, db_session: AsyncSession, seed_data):
    """Test checking pending reports for a date (identifying missing branches)."""
    # AGM token
    token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch pending reports. Both branches (PADI, COIMBATORE) should be pending initially
    response = client.get("/api/v1/reports/pending?report_date=2026-07-16", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    codes = {b["branch_code"] for b in data}
    assert "PADI" in codes
    assert "COIMBATORE" in codes

    # Upload report for Padi
    mgr_token = await get_jwt_token(client, "padi@pothys.com", "managerPassword123")
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}
    client.post(
        "/api/v1/reports/upload",
        headers=mgr_headers,
        data={
            "report_date": "2026-07-16",
            "sales_amount": 400000,
            "attendance_count": 30,
            "target_achievement": 100
        }
    )

    # Re-check pending reports. Only Coimbatore should be missing now
    response2 = client.get("/api/v1/reports/pending?report_date=2026-07-16", headers=headers)
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2) == 1
    assert data2[0]["branch_code"] == "COIMBATORE"


async def test_upload_report_manager_forced_branch(client: TestClient, db_session: AsyncSession, seed_data):
    """Verify that reports uploaded by a Manager are always forced to their assigned branch."""
    token = await get_jwt_token(client, "padi@pothys.com", "managerPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    # Manager of Padi uploads a report containing text matching Coimbatore Mahal
    mock_extracted_text = "Pothys Daily Report\nBranch: Coimbatore Mahal\nSales: Rs. 600,000\nAttendance: 28\nTarget Achievement: 98%"

    with patch("app.services.storage.storage_service.upload_file", return_value="/uploads/mock_padi.pdf") as mock_upload, \
         patch("app.services.doc_parser.DocumentParser.extract_text_from_pdf", return_value=mock_extracted_text) as mock_pdf_extract:
         
        response = client.post(
            "/api/v1/reports/upload",
            headers=headers,
            data={
                "report_date": "2026-07-16"
            },
            files={"file": ("report.pdf", b"dummy contents", "application/pdf")}
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # The report must be forced to Padi branch, ignoring the Coimbatore content in the file!
        assert data["branch_id"] == str(seed_data["branch_padi"].id)
        assert data["sales_amount"] == 600000.0
        
        # Verify in DB
        db_res = await db_session.execute(
            select(DailyReport).where(DailyReport.branch_id == seed_data["branch_padi"].id)
        )
        report = db_res.scalars().first()
        assert report is not None
        assert report.sales_amount == 600000.0


async def test_upload_report_triggers_notification(client: TestClient, db_session: AsyncSession, seed_data):
    """Verify that uploading a report immediately creates a 'Report Submitted' notification for AGM."""
    token = await get_jwt_token(client, "padi@pothys.com", "managerPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/reports/upload",
        headers=headers,
        data={
            "report_date": date.today().strftime("%Y-%m-%d"),
            "sales_amount": 450000.0,
            "attendance_count": 42,
            "target_achievement": 90.0,
            "inventory_status": "Gold is stable.",
            "remarks": "None.",
            "issues": "None."
        }
    )
    assert response.status_code == 201

    # Check that a notification was created for the AGM user
    agm_token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    agm_headers = {"Authorization": f"Bearer {agm_token}"}
    
    notif_res = client.get("/api/v1/notifications/", headers=agm_headers)
    assert notif_res.status_code == 200
    notifs = notif_res.json()
    
    # Find Report Submitted notification for Padi
    submitted_notif = next((n for n in notifs if "Report Submitted" in n["title"] and n["branch_id"] == str(seed_data["branch_padi"].id)), None)
    assert submitted_notif is not None
    assert submitted_notif["branch_id"] == str(seed_data["branch_padi"].id)


async def test_overdue_pending_notification(client: TestClient, db_session: AsyncSession, seed_data):
    """Verify that after the configured submission time, pending reports create notifications."""
    agm_token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    agm_headers = {"Authorization": f"Bearer {agm_token}"}

    # Case 1: Before deadline (set REPORT_SUBMISSION_TIME to 23:59)
    with patch("app.core.config.settings.REPORT_SUBMISSION_TIME", "23:59"):
        response = client.get("/api/v1/notifications/", headers=agm_headers)
        assert response.status_code == 200
        notifs = response.json()
        
        # There should be NO pending notifications for today's reports
        pending_notifs = [n for n in notifs if "Report Pending" in n["title"]]
        assert len(pending_notifs) == 0

    # Case 2: Past deadline (set REPORT_SUBMISSION_TIME to 00:00)
    with patch("app.core.config.settings.REPORT_SUBMISSION_TIME", "00:00"):
        response = client.get("/api/v1/notifications/", headers=agm_headers)
        assert response.status_code == 200
        notifs = response.json()
        
        # There should be pending notifications generated for the unsubmitted branches (Padi and Coimbatore)
        pending_notifs = [n for n in notifs if "Report Pending" in n["title"]]
        assert len(pending_notifs) == 2
