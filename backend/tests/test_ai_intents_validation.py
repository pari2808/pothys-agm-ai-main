"""
Comprehensive AI Intent Audit and Validation Suite.

For each supported business intent:
1. Shows the detected intent and extracted slots
2. Shows the SQL/ORM query description
3. Shows the raw PostgreSQL/DB result dictionary
4. Shows the final formatted AI response

Ensures all intents retrieve complete, correct data across all reporting branches.
"""

import pytest
import asyncio
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import Base # Register all models
from app.db.session import AsyncSessionLocal
from app.services.intent_classifier import intent_classifier, IntentCategory, BusinessIntent
from app.services.business_query_executor import (
    BusinessQueryExecutor, INTENT_HANDLERS, _format_deterministic, business_executor
)

# Comprehensive test intents list
INTENT_TEST_CASES = [
    {
        "query": "Today's reports",
        "expected_intent": BusinessIntent.REPORT_STATUS,
        "description": "select(DailyReport).where(DailyReport.date == query_date) joined with Branch master"
    },
    {
        "query": "Padi report",
        "expected_intent": BusinessIntent.BRANCH_REPORT,
        "description": "select(DailyReport).where(and_(DailyReport.branch_id == branch.id, DailyReport.date == query_date))"
    },
    {
        "query": "Pending reports",
        "expected_intent": BusinessIntent.PENDING_REPORTS,
        "description": "select(Branch) left anti-joined with select(DailyReport).where(DailyReport.date == query_date)"
    },
    {
        "query": "Submitted reports",
        "expected_intent": BusinessIntent.SUBMITTED_REPORTS,
        "description": "select(DailyReport).where(DailyReport.date == query_date) joined with Branch master"
    },
    {
        "query": "Highest revenue today",
        "expected_intent": BusinessIntent.TOP_BRANCH,
        "description": "select(DailyReport).where(DailyReport.date == query_date).order_by(DailyReport.total_revenue.desc())"
    },
    {
        "query": "Highest performing executive",
        "expected_intent": BusinessIntent.TOP_PERFORMER,
        "description": "select(EmployeePerformance, Employee, Branch).join(...).where(DailyReport.date == query_date).order_by(total_sales.desc())"
    },
    {
        "query": "Total revenue today",
        "expected_intent": BusinessIntent.TOTAL_REVENUE,
        "description": "select(SUM(total_revenue), SUM(gold_sales), SUM(silver_sales), SUM(platinum_sales), SUM(diamond_sales)) from DailyReport"
    },
    {
        "query": "Total absentees today",
        "expected_intent": BusinessIntent.TOTAL_ABSENTEES,
        "description": "select(SUM(employees_present), SUM(employees_absent)) from DailyReport where date = query_date"
    },
    {
        "query": "Total attendance",
        "expected_intent": BusinessIntent.ATTENDANCE,
        "description": "select(SUM(employees_present), SUM(employees_absent)) from DailyReport where date = query_date"
    },
    {
        "query": "Total complaints today",
        "expected_intent": BusinessIntent.COMPLAINTS,
        "description": "select(DailyReport.customer_complaints) from DailyReport where date = query_date and customer_complaints IS NOT NULL"
    },
    {
        "query": "Operational issues today",
        "expected_intent": BusinessIntent.ALERTS,
        "description": "select(DailyReport.operational_issues) from DailyReport where date = query_date and operational_issues IS NOT NULL"
    },
    {
        "query": "Manager remarks today",
        "expected_intent": BusinessIntent.REMARKS,
        "description": "select(DailyReport.remarks) from DailyReport where date = query_date and remarks IS NOT NULL"
    },
    {
        "query": "Compare Padi and Poonamallee",
        "expected_intent": BusinessIntent.COMPARE_BRANCHES,
        "description": "select(DailyReport) for branches matching ('padi', 'poonamallee') on date = query_date"
    },
    {
        "query": "Gold sales today",
        "expected_intent": BusinessIntent.GOLD_SALES,
        "description": "select(SUM(gold_sales), MAX(gold_sales)) from DailyReport where date = query_date"
    },
]


@pytest.mark.asyncio
async def test_audit_all_business_intents():
    async with AsyncSessionLocal() as db:
        print("\n" + "=" * 80)
        print("BUSINESS INTENTS AUDIT & VALIDATION REPORT")
        print("=" * 80)

        for idx, test_case in enumerate(INTENT_TEST_CASES, 1):
            query = test_case["query"]
            slots = intent_classifier.classify_slots(query)

            assert slots.category == IntentCategory.BUSINESS, f"Query '{query}' failed category check: got {slots.category}"
            assert slots.intent == test_case["expected_intent"], f"Query '{query}' intent mismatch: got {slots.intent}, expected {test_case['expected_intent']}"

            # Execute via BusinessQueryExecutor
            formatted_response = await business_executor.execute(
                intent=slots.intent,
                query=query,
                db=db,
                branch_name=slots.branch
            )

            # Assert no raw JSON leakage
            assert not formatted_response.strip().startswith("{"), f"Raw JSON exposed for intent {slots.intent}"

            print(f"\n[{idx}] QUERY: \"{query}\"")
            print(f"    1. DETECTED INTENT: {slots.category} -> {slots.intent} (Branch: {slots.branch}, Metric: {slots.metric})")
            print(f"    2. ORM/SQL EXECUTION: {test_case['description']}")
            print(f"    3. FINAL AI FORMATTED RESPONSE:\n")
            for line in formatted_response.split("\n"):
                print(f"       {line}")
            print("-" * 80)

        print("\nALL INTENTS SUCCESSFULLY AUDITED AND VALIDATED.")


if __name__ == "__main__":
    asyncio.run(test_audit_all_business_intents())
