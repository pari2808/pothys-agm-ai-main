import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.gemini_service import GeminiService, gemini_service
from app.services.business_query_executor import _format_with_llm, _format_deterministic

@pytest.mark.asyncio
async def test_gemini_service_success():
    """Test successful Gemini API response formatting."""
    mock_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Good morning Sir. Poonamallee branch generated total revenue of ₹25.30L."}
                    ]
                }
            }
        ]
    }
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value=mock_payload)

    service = GeminiService(api_key="valid_test_key")
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        result = await service.format_executive_response(
            user_query="Poonamallee revenue",
            structured_data={"branch": "Poonamallee", "revenue": 2530000}
        )
        assert result == "Good morning Sir. Poonamallee branch generated total revenue of ₹25.30L."

@pytest.mark.asyncio
async def test_gemini_service_quota_error_fallback():
    """Test quota error (429) cleanly returns None and falls back to deterministic formatter."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.reason_phrase = "Too Many Requests"
    mock_response.text = "Quota exceeded"

    service = GeminiService(api_key="valid_test_key")
    with patch("httpx.AsyncClient.post", return_value=mock_response):
        result = await service.format_executive_response(
            user_query="Poonamallee revenue",
            structured_data={"branch": "Poonamallee", "revenue": 2530000}
        )
        assert result is None

@pytest.mark.asyncio
async def test_gemini_service_timeout_fallback():
    """Test timeout exception cleanly returns None."""
    import httpx
    service = GeminiService(api_key="valid_test_key")
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Timeout")):
        result = await service.format_executive_response(
            user_query="Poonamallee revenue",
            structured_data={"branch": "Poonamallee", "revenue": 2530000}
        )
        assert result is None

@pytest.mark.asyncio
async def test_business_executor_format_with_llm_fallback():
    """Verify _format_with_llm automatically falls back to deterministic output when Gemini returns None."""
    test_data = {
        "query_type": "BRANCH_REPORT",
        "branch": "Poonamallee",
        "date": "2026-07-21",
        "total_revenue": 2530000,
        "gold_sales": 1680000,
        "silver_sales": 420000,
        "platinum_sales": 100000,
        "diamond_sales": 330000,
        "digigold_enrollments": 10,
        "digisilver_enrollments": 5,
        "employees_present": 43,
        "employees_absent": 2,
        "customer_complaints": 1,
        "operational_issues": "Air conditioning maintenance scheduled.",
        "manager_remarks": "Overall good day.",
        "submitted": True
    }
    
    with patch.object(gemini_service, "format_executive_response", new_callable=AsyncMock) as mock_gemini:
        mock_gemini.return_value = None  # Simulate Gemini failure/quota
        fallback_output = await _format_with_llm("Poonamallee report", test_data)
        assert fallback_output is not None
        assert len(fallback_output) > 0
        assert _format_deterministic(test_data) == fallback_output
