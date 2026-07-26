"""
Comprehensive Automated Test Suite: 56 Diverse AGM Questions.
Validates slot extraction, intent detection, fuzzy branch matching, and response granularity.
"""

import pytest
import asyncio
from app.db.base import Base
from app.db.session import AsyncSessionLocal
from app.services.intent_classifier import (
    IntentClassifier, IntentCategory, BusinessIntent, StaticIntent, intent_classifier
)
from app.services.business_query_executor import business_executor

TEST_QUESTIONS = [
    # ── 1-4. Branch Attendance Queries (Fuzzy + Specific Metric) ──
    {
        "query": "Attendance in Poonamallee",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Poonamallee",
        "expected_metric": "attendance",
        "forbidden_in_output": ["Revenue", "Gold", "Complaints", "Remarks"]
    },
    {
        "query": "Poonamallee attendance",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Poonamallee",
        "expected_metric": "attendance",
        "forbidden_in_output": ["Revenue", "Gold", "Complaints"]
    },
    {
        "query": "ponamallee staff attendance",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Poonamallee",
        "expected_metric": "attendance",
        "forbidden_in_output": ["Revenue", "Gold"]
    },
    {
        "query": "poonamale absent count",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Poonamallee",
        "expected_metric": "attendance",
        "forbidden_in_output": ["Revenue", "Gold"]
    },

    # ── 5-7. Branch Gold Sales Queries ──
    {
        "query": "Gold sales in Poonamallee",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Poonamallee",
        "expected_metric": "gold_sales",
        "forbidden_in_output": ["Attendance", "Complaints", "Remarks"]
    },
    {
        "query": "Poonamallee gold sales",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Poonamallee",
        "expected_metric": "gold_sales",
        "forbidden_in_output": ["Attendance", "Complaints"]
    },
    {
        "query": "poonamale gold revenue",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Poonamallee",
        "expected_metric": "gold_sales",
        "forbidden_in_output": ["Attendance", "Complaints"]
    },

    # ── 8-10. Branch Full Report Queries ──
    {
        "query": "Poonamallee report",
        "expected_intent": BusinessIntent.BRANCH_REPORT,
        "expected_branch": "Poonamallee",
        "expected_metric": None
    },
    {
        "query": "poonamale daily report",
        "expected_intent": BusinessIntent.BRANCH_REPORT,
        "expected_branch": "Poonamallee",
        "expected_metric": None
    },
    {
        "query": "give me poonamallee report",
        "expected_intent": BusinessIntent.BRANCH_REPORT,
        "expected_branch": "Poonamallee",
        "expected_metric": None
    },

    # ── 11-13. Comparison Queries ──
    {
        "query": "Compare Padi and Poonamallee",
        "expected_intent": BusinessIntent.COMPARE_BRANCHES,
        "expected_branches": ["Padi", "Poonamallee"]
    },
    {
        "query": "Padi vs Poonamallee",
        "expected_intent": BusinessIntent.COMPARE_BRANCHES,
        "expected_branches": ["Padi", "Poonamallee"]
    },
    {
        "query": "difference between padi and poonamallee",
        "expected_intent": BusinessIntent.COMPARE_BRANCHES,
        "expected_branches": ["Padi", "Poonamallee"]
    },

    # ── 14-16. Total Absentees Queries ──
    {
        "query": "Total absent today",
        "expected_intent": BusinessIntent.TOTAL_ABSENTEES,
        "expected_metric": "attendance"
    },
    {
        "query": "total absentees",
        "expected_intent": BusinessIntent.TOTAL_ABSENTEES,
        "expected_metric": "attendance"
    },
    {
        "query": "how many staff absent today",
        "expected_intent": BusinessIntent.TOTAL_ABSENTEES,
        "expected_metric": "attendance"
    },

    # ── 17-19. Total Revenue Queries ──
    {
        "query": "Total revenue today",
        "expected_intent": BusinessIntent.TOTAL_REVENUE,
        "expected_metric": "total_revenue"
    },
    {
        "query": "gross revenue today",
        "expected_intent": BusinessIntent.TOTAL_REVENUE,
        "expected_metric": "total_revenue"
    },
    {
        "query": "total sales today",
        "expected_intent": BusinessIntent.TOTAL_REVENUE,
        "expected_metric": "total_revenue"
    },

    # ── 20-22. Total Silver Sales Queries ──
    {
        "query": "Total silver sales",
        "expected_intent": BusinessIntent.TOTAL_METRIC,
        "expected_metric": "silver_sales",
        "forbidden_in_output": ["Report Status", "Pending Branches"]
    },
    {
        "query": "overall silver sales",
        "expected_intent": BusinessIntent.TOTAL_METRIC,
        "expected_metric": "silver_sales"
    },
    {
        "query": "silver revenue today",
        "expected_intent": BusinessIntent.TOTAL_METRIC,
        "expected_metric": "silver_sales"
    },

    # ── 23-25. Chromepet Branch Queries (Fuzzy) ──
    {
        "query": "Chromepet report",
        "expected_intent": BusinessIntent.BRANCH_REPORT,
        "expected_branch": "Chromepet"
    },
    {
        "query": "chrompet report",
        "expected_intent": BusinessIntent.BRANCH_REPORT,
        "expected_branch": "Chromepet"
    },
    {
        "query": "chromepett status",
        "expected_intent": BusinessIntent.BRANCH_REPORT,
        "expected_branch": "Chromepet"
    },

    # ── 26-28. Coimbatore Branch Queries ──
    {
        "query": "Coimbatore attendance",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Coimbatore",
        "expected_metric": "attendance"
    },
    {
        "query": "kovai staff present",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Coimbatore",
        "expected_metric": "attendance"
    },
    {
        "query": "coimbatore branch absentees",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Coimbatore",
        "expected_metric": "attendance"
    },

    # ── 29-30. Trichy Branch Queries ──
    {
        "query": "Trichy gold sales",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Trichy",
        "expected_metric": "gold_sales"
    },
    {
        "query": "tiruchirappalli gold revenue",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Trichy",
        "expected_metric": "gold_sales"
    },

    # ── 31-33. Trivandrum Branch Queries ──
    {
        "query": "Trivandrum revenue",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Trivandrum",
        "expected_metric": "total_revenue"
    },
    {
        "query": "trivandrum sales amount",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Trivandrum",
        "expected_metric": "total_revenue"
    },
    {
        "query": "thiruvananthapuram turnover",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Trivandrum",
        "expected_metric": "total_revenue"
    },

    # ── 34-35. Tirunelveli Branch Complaints ──
    {
        "query": "Tirunelveli complaints",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Tirunelveli",
        "expected_metric": "complaints"
    },
    {
        "query": "nellai customer issues",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Tirunelveli",
        "expected_metric": "complaints"
    },

    # ── 36-37. Salem Branch Remarks ──
    {
        "query": "Salem remarks",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Salem",
        "expected_metric": "remarks"
    },
    {
        "query": "salem manager comment",
        "expected_intent": BusinessIntent.BRANCH_METRIC,
        "expected_branch": "Salem",
        "expected_metric": "remarks"
    },

    # ── 38-40. Pending Reports Queries ──
    {
        "query": "Pending reports",
        "expected_intent": BusinessIntent.PENDING_REPORTS
    },
    {
        "query": "who has not submitted",
        "expected_intent": BusinessIntent.PENDING_REPORTS
    },
    {
        "query": "branches yet to submit",
        "expected_intent": BusinessIntent.PENDING_REPORTS
    },

    # ── 41-42. Submitted Reports Queries ──
    {
        "query": "Submitted reports",
        "expected_intent": BusinessIntent.SUBMITTED_REPORTS
    },
    {
        "query": "which branches submitted",
        "expected_intent": BusinessIntent.SUBMITTED_REPORTS
    },

    # ── 43-45. Top Branch Queries ──
    {
        "query": "Highest revenue today",
        "expected_intent": BusinessIntent.TOP_BRANCH
    },
    {
        "query": "best performing branch",
        "expected_intent": BusinessIntent.TOP_BRANCH
    },
    {
        "query": "leading store today",
        "expected_intent": BusinessIntent.TOP_BRANCH
    },

    # ── 46-48. Top Performer Queries ──
    {
        "query": "Highest performing executive",
        "expected_intent": BusinessIntent.TOP_PERFORMER
    },
    {
        "query": "best salesperson today",
        "expected_intent": BusinessIntent.TOP_PERFORMER
    },
    {
        "query": "top employee today",
        "expected_intent": BusinessIntent.TOP_PERFORMER
    },

    # ── 49-50. Agenda Queries ──
    {
        "query": "Today's agenda",
        "expected_intent": BusinessIntent.AGENDA
    },
    {
        "query": "executive schedule today",
        "expected_intent": BusinessIntent.AGENDA
    },

    # ── 51-52. Meetings Queries ──
    {
        "query": "Upcoming meetings",
        "expected_intent": BusinessIntent.MEETINGS
    },
    {
        "query": "corporate meetings today",
        "expected_intent": BusinessIntent.MEETINGS
    },

    # ── 53-54. Tasks Queries ──
    {
        "query": "Pending tasks",
        "expected_intent": BusinessIntent.TASKS
    },
    {
        "query": "action items today",
        "expected_intent": BusinessIntent.TASKS
    },

    # ── 55-56. Knowledge & Static Guardrails ──
    {
        "query": "What is the SOP for gold exchange?",
        "expected_category": IntentCategory.KNOWLEDGE
    },
    {
        "query": "How do I write a python function?",
        "expected_category": IntentCategory.STATIC,
        "expected_intent": StaticIntent.OUT_OF_DOMAIN
    }
]


@pytest.mark.asyncio
async def test_50_queries_slot_extraction_and_granularity():
    """Verify all 56 AGM queries produce exact slots and granular outputs."""
    async with AsyncSessionLocal() as db:
        print(f"\n{'='*80}\nSTARTING 56-QUERY SLOT CLASSIFICATION & GRANULARITY SUITE\n{'='*80}")

        passed_count = 0
        for idx, tc in enumerate(TEST_QUESTIONS, 1):
            q = tc["query"]
            slots = intent_classifier.classify_slots(q)

            # Check Category
            if "expected_category" in tc:
                assert slots.category == tc["expected_category"], f"Query [{idx}] '{q}': Category mismatch. Got {slots.category}, expected {tc['expected_category']}"

            # Check Intent
            if "expected_intent" in tc:
                assert slots.intent == tc["expected_intent"], f"Query [{idx}] '{q}': Intent mismatch. Got {slots.intent}, expected {tc['expected_intent']}"

            # Check Branch
            if "expected_branch" in tc:
                assert slots.branch == tc["expected_branch"], f"Query [{idx}] '{q}': Branch mismatch. Got {slots.branch}, expected {tc['expected_branch']}"

            # Check Branches (for comparison)
            if "expected_branches" in tc:
                for eb in tc["expected_branches"]:
                    assert eb in slots.branches, f"Query [{idx}] '{q}': Expected branch '{eb}' in branches list {slots.branches}"

            # Check Metric
            if "expected_metric" in tc:
                assert slots.metric == tc["expected_metric"], f"Query [{idx}] '{q}': Metric mismatch. Got {slots.metric}, expected {tc['expected_metric']}"

            # If it's a business query, execute and verify output granularity
            if slots.category == IntentCategory.BUSINESS:
                output = await business_executor.execute(
                    intent=slots.intent,
                    query=q,
                    db=db,
                    branch_name=slots.branch
                )
                assert output and len(output) > 0, f"Query [{idx}] '{q}': Empty response"

                if "forbidden_in_output" in tc:
                    for forbidden in tc["forbidden_in_output"]:
                        assert forbidden.lower() not in output.lower(), f"Query [{idx}] '{q}': Forbidden keyword '{forbidden}' appeared in output! Response: {output}"

            passed_count += 1
            print(f"[{idx:02d}/56] PASSED: \"{q}\" -> Intent: {slots.intent} | Branch: {slots.branch} | Metric: {slots.metric}")

        print(f"\n{'='*80}\nALL {passed_count} AGM QUERIES PASSED WITH 100% PRECISION!\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(test_50_queries_slot_extraction_and_granularity())
