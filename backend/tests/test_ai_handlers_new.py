import pytest
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.branch import Branch
from app.models.report import DailyReport
from app.models.meeting import Meeting
from app.models.ai_memory import AIMemory
from app.services.business_query_executor import business_executor
from app.services.intent_classifier import intent_classifier, BusinessIntent
from tests.test_ai import get_jwt_token, seed_ai_data  # reuse fixture

@pytest.mark.asyncio
async def test_compare_branches_validation(db_session: AsyncSession, seed_ai_data):
    """Verify comparison validation returns professional message when either report is missing."""
    seed = seed_ai_data
    # Delete Coimbatore report for 2026-07-16
    await db_session.delete(seed["report_coimbatore"])
    await db_session.commit()

    # Query comparison for Padi and Coimbatore on 2026-07-16
    res = await business_executor.execute(
        intent=BusinessIntent.COMPARE_BRANCHES,
        query="Compare Padi and Coimbatore yesterday",  # trigger yesterday (2026-07-16 relative to test environment dates if mock is yesterday)
        db=db_session,
        current_user=seed["agm"]
    )
    
    assert "has not submitted" in res
    assert "so a comparison cannot be generated" in res


@pytest.mark.asyncio
async def test_meeting_scheduling_flow_and_postgres_saving(client: TestClient, db_session: AsyncSession, seed_ai_data):
    """Test step-by-step meeting scheduling state machine and final save to PostgreSQL."""
    seed = seed_ai_data
    token = await get_jwt_token(client, "agm@pothys.com", "agmPassword123")
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Start scheduling
    response1 = client.post(
        "/api/v1/ai/query",
        headers=headers,
        json={"content": "Create a meeting"}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    conv_id = data1["conversation_id"]

    # Verify AIMemory state exists
    state_key = f"meeting_creation_{conv_id}"
    stmt = select(AIMemory).where(AIMemory.key == state_key)
    res = await db_session.execute(stmt)
    memory_state = res.scalars().first()
    assert memory_state is not None
    assert memory_state.value["title"] is None

    # Step 2: Feed missing parameters via mocked slot extraction
    mock_slots_step2 = {
        "title": "Strategy Discussion",
        "date": "2026-07-25",
        "time": "10:00",
        "duration": 60,
        "participants": ["Padi manager"],
        "branch": "Padi",
        "notes": "Discuss Q3 goals and silver sales targets."
    }

    with patch("app.services.gemini_service.gemini_service.extract_meeting_slots", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = mock_slots_step2
        
        response2 = client.post(
            "/api/v1/ai/query",
            headers=headers,
            json={"conversation_id": conv_id, "content": "Schedule meeting for Strategy Discussion on 25th July at 10am for 1h with Padi manager at Padi store."}
        )
        assert response2.status_code == 200
        data2 = response2.json()

        # Check success response
        assert "Strategy Discussion" in data2["content"]
        assert "Scheduled" in data2["content"]

    # Verify state is cleared in AIMemory
    res = await db_session.execute(stmt)
    memory_state = res.scalars().first()
    assert memory_state is None

    # Verify Meeting is saved in PostgreSQL
    meet_stmt = select(Meeting).where(Meeting.title.like("%Strategy Discussion%"))
    meet_res = await db_session.execute(meet_stmt)
    meeting = meet_res.scalars().first()
    assert meeting is not None
    assert meeting.agenda == "Discuss Q3 goals and silver sales targets."
    assert meeting.organizer_id == seed["agm"].id


@pytest.mark.asyncio
async def test_exception_safety_boundary(db_session: AsyncSession, seed_ai_data):
    """Test that all exceptions are caught internally and return professional business responses instead of python exceptions."""
    seed = seed_ai_data

    # Mock handler to raise an error
    with patch("app.services.business_query_executor.HANDLERS") as mock_handlers:
        mock_handler = AsyncMock()
        mock_handler.handle.side_effect = RuntimeError("Database connection timed out or is dead")
        mock_handlers.get.return_value = mock_handler

        res = await business_executor.execute(
            intent=BusinessIntent.GET_GOLD_SALES,
            query="Gold sales today",
            db=db_session,
            current_user=seed["agm"]
        )

        # Assert no traceback exposure
        assert "RuntimeError" not in res
        assert "Database connection timed out" not in res
        assert "I encountered a processing error" in res


def test_strip_markdown():
    """Verify that strip_markdown completely strips markdown headers, bold, and raw markers."""
    from app.services.business_query_executor import strip_markdown
    raw_text = "### Padi Reports Summary\n- **Gold**: Rs. 15.00L\n- **Silver**: Rs. 2.50L\n`success`"
    cleaned = strip_markdown(raw_text)
    assert "#" not in cleaned
    assert "*" not in cleaned
    assert "`" not in cleaned
    assert "Padi Reports Summary" in cleaned
    assert "Gold: Rs. 15.00L" in cleaned


def test_filter_metrics_by_slots():
    """Verify that filter_metrics_by_slots filters dict elements to only the requested slots."""
    from app.services.business_query_executor import filter_metrics_by_slots
    from app.services.intent_classifier import QuerySlots
    
    mock_data = {
        "query_type": "BRANCH_REPORT",
        "branch": "Padi",
        "date": "2026-07-21",
        "total_revenue": 1000000.0,
        "gold_sales": 600000.0,
        "silver_sales": 200000.0,
        "employees_present": 42
    }
    
    slots = QuerySlots(
        intent="GET_GOLD_SALES",
        category="BUSINESS",
        metrics=["gold_sales", "silver_sales"]
    )
    
    filtered = filter_metrics_by_slots(mock_data, slots)
    assert filtered["gold_sales"] == 600000.0
    assert filtered["silver_sales"] == 200000.0
    assert "total_revenue" not in filtered
    assert "employees_present" not in filtered


@pytest.mark.asyncio
async def test_compound_metrics_response_plain_text(db_session: AsyncSession, seed_ai_data):
    """Verify query execution for compound metrics filters database outputs and removes markdown."""
    seed = seed_ai_data
    from app.services.intent_classifier import QuerySlots
    
    # Seed a report for today dynamically
    r_today = DailyReport(
        branch_id=seed["branch_padi"].id,
        manager_id=seed["manager"].id,
        date=date.today(),
        sales_amount=450000.0,
        attendance_count=35,
        target_achievement=90.0,
        remarks="Excellent sales walkins",
        issues="No issues",
        gold_sales=120000.0,
        silver_sales=45000.0,
        total_revenue=450000.0,
        employees_present=35
    )
    db_session.add(r_today)
    await db_session.commit()
    
    # Mock classifier slots to simulate compound natural language query: "Give only the gold and silver sales in Padi today"
    mock_slots = QuerySlots(
        intent="BRANCH_REPORT",
        category="BUSINESS",
        branch="Padi",
        metrics=["gold_sales", "silver_sales"],
        time="today"
    )
    
    with patch("app.services.intent_classifier.intent_classifier.classify_slots_async", new_callable=AsyncMock) as mock_slots_call:
        mock_slots_call.return_value = mock_slots
        
        response = await business_executor.execute(
            intent="BRANCH_REPORT",
            query="Give only the gold and silver sales in Padi today",
            db=db_session,
            current_user=seed["agm"]
        )
        
        # Verify no markdown formatting tags exist
        assert "**" not in response
        assert "###" not in response
        assert "•" not in response
        # Verify only requested metrics are visible
        assert "Gold:" in response
        assert "Silver:" in response
        assert "Revenue:" not in response
        assert "Attendance:" not in response

