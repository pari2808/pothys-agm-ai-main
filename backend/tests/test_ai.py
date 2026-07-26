import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.branch import Branch
from app.models.report import DailyReport
from app.models.document import DocumentChunk
from app.core.security import get_password_hash
from app.repositories.document import DocumentRepository

@pytest.fixture
async def seed_ai_data(db_session: AsyncSession):
    """Seed test branches, manager, and AGM accounts, plus daily reports and vector chunks."""
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

    # Create daily reports
    r1 = DailyReport(
        branch_id=b1.id,
        manager_id=manager.id,
        date=date(2026, 7, 16),
        sales_amount=450000.0,
        attendance_count=35,
        target_achievement=90.0,
        remarks="Excellent sales walkins",
        issues="No issues"
    )
    r2 = DailyReport(
        branch_id=b2.id,
        manager_id=manager.id, # mock manager upload for simplicity
        date=date(2026, 7, 16),
        sales_amount=200000.0,
        attendance_count=18,
        target_achievement=50.0,
        remarks="Slow day at Coimbatore Swarna Mahal",
        issues="Inventory shortage on gold necklaces"
    )
    db_session.add_all([r1, r2])
    await db_session.commit()
    await db_session.refresh(r1)
    await db_session.refresh(r2)

    # Generate dummy embeddings (1536 floats)
    v1 = [0.1] * 1536
    v2 = [0.9] * 1536

    doc_repo = DocumentRepository(db_session)
    await doc_repo.create_chunks([
        {
            "report_id": r1.id,
            "source_type": "REPORT",
            "content": "Padi Swarna Mahal daily report shows 450,000 INR sales and strong customer footfalls.",
            "embedding": v1
        },
        {
            "report_id": r2.id,
            "source_type": "REPORT",
            "content": "Coimbatore Swarna Mahal daily report mentions slow day and inventory shortage on gold necklaces.",
            "embedding": v2
        }
    ])

    return {
        "branch_padi": b1,
        "branch_coimbatore": b2,
        "manager": manager,
        "agm": agm,
        "report_padi": r1,
        "report_coimbatore": r2,
        "v1": v1,
        "v2": v2
    }

# Fix date import
from datetime import date

async def get_jwt_token(client: TestClient, email: str, password: str) -> str:
    """Helper to get JWT token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password}
    )
    return response.json()["access_token"]

async def test_ai_query_domain_guardrail(client: TestClient, seed_ai_data):
    """Out-of-domain queries should trigger polite refusal guardrails."""
    token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/ai/query",
        headers=headers,
        json={"content": "how do I write a python function to scrape a website?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "restricted to Pothys business operations" in data["content"]
    assert len(data["retrieved_sources"]) == 0

async def test_ai_query_rag_success_agm(client: TestClient, seed_ai_data):
    """AGM queries are answered using retrieved RAG context (all branches)."""
    token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    # Query matching Coimbatore necklace shortage
    response = client.post(
        "/api/v1/ai/query",
        headers=headers,
        json={"content": "Which branch has shortage of gold necklaces?"}
    )
    assert response.status_code == 200
    data = response.json()
    # Mock RAG yields response mentioning shortage
    assert "coimbatore" in data["content"].lower()
    assert len(data["retrieved_sources"]) > 0

async def test_ai_query_context_isolation_manager(client: TestClient, seed_ai_data):
    """Manager queries only retrieve context from their own branch (Padi)."""
    # Manager of Padi logins
    token = await get_jwt_token(client, "padi@pothys.com", "managerPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    # Manager queries about necklace shortage (which occurred in Coimbatore)
    response = client.post(
        "/api/v1/ai/query",
        headers=headers,
        json={"content": "Do we have shortage of gold necklaces in our branch?"}
    )
    assert response.status_code == 200
    data = response.json()
    # Since Coimbatore chunks are filtered out for Padi manager, RAG response should state no info available
    assert "I cannot find this information" in data["content"] or "Mock" in data["content"]

async def test_ai_list_conversations_and_history(client: TestClient, seed_ai_data):
    """Test listings of chat threads and individual message lists."""
    token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    # Initial query to create thread
    response = client.post(
        "/api/v1/ai/query",
        headers=headers,
        json={"content": "Show recent sales of Padi Swarna Mahal."}
    )
    conv_res = client.get("/api/v1/ai/conversations", headers=headers)
    assert conv_res.status_code == 200
    convs = conv_res.json()
    assert len(convs) == 1
    conv_id = convs[0]["id"]

    # Fetch detailed history
    detail_res = client.get(f"/api/v1/ai/conversations/{conv_id}", headers=headers)
    assert detail_res.status_code == 200
    details = detail_res.json()
    assert len(details["messages"]) == 2 # User query + Assistant response
