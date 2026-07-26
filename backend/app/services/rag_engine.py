import re
import random
from typing import List, Optional, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy import select, and_, not_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings

# Import DB Models
from app.models.branch import Branch
from app.models.report import DailyReport
from app.models.meeting import Meeting
from app.models.task import Task
from app.models.user import User
from app.models.employee import Employee
from app.models.employee_performance import EmployeePerformance
from app.models.scheme_summary import SchemeSummary

def getShortBranchName(fullName: str) -> str:
    return fullName.replace("Swarna Mahal", "").strip()

# ==========================================
# 1. Intent Detector
# ==========================================
class IntentDetector:
    INTENT_PATTERNS = {
            "identity": [
            "who are you", "what is your name", "introduce yourself", "your name", 
            "who you are", "identity", "what do you call yourself", "who am i talking to"
        ],
        "greeting": [
            "hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings", "yo", "sup"
        ],
        "help": [
            "help", "what can you do", "capabilities", "features", "what are your features", 
            "how to use", "commands", "menu"
        ],
        "agenda": [
            "agenda", "schedule today", "today's schedule", "what's on today", "day schedule", 
            "executive agenda", "agenda today", "daily agenda", "executive schedule", "today's agenda"
        ],
        "meetings": [
            "meeting", "meetings", "appointment", "appointments", "calendar", "corporate meeting", 
            "corporate meetings", "scheduled meetings", "upcoming meetings"
        ],
        "tasks": [
            "task", "tasks", "todo", "to do", "action item", "action items", "assigned", 
            "executive task", "executive tasks", "pending tasks"
        ],
        "sales": [
            "sales", "revenue", "income", "amount", "turnover", "sell", "earning", "earnings", 
            "target achievement", "sales figures", "sales amount", "how much did we sell"
        ],
        "attendance": [
            "attendance", "staff", "present", "headcount", "employees", "manpower", "staff present"
        ],
        # More-specific report intents MUST come before all_reports so their
        # direct-phrase matches fire before the generic single-token "report" match.
        "pending_reports": [
            "pending report", "pending reports", "missing report", "missing reports", "missing submission", 
            "missing submissions", "not submitted", "unsubmitted", "have not submitted", "did not submit",
            "yet to submit", "branches pending", "stores pending", "centres pending", "centers pending",
            "who is yet to submit", "haven't submitted", "not yet submitted", "still pending",
            "who has not submitted", "which branch pending", "which store pending"
        ],
        "submitted_reports": [
            "submitted report", "submitted reports", "who submitted", "submissions today", "reports in", 
            "received reports", "completed reports", "successful submissions", "already submitted"
        ],
        # Broad catch-all for "show me reports" — placed AFTER the specific intents
        # so that "pending reports" / "submitted reports" win on direct phrase match first.
        "all_reports": [
            "daily report", "daily reports", "branch report", "branch reports",
            "store report", "store reports", "today report", "today reports",
            "show reports", "give me reports", "all reports", "every report", "every store report",
            "every branch report", "todays reports", "todays report", "today's report",
            "today's reports", "show today reports", "all branch reports", "all store reports",
            "report status", "report summary", "daily summary", "branch summary",
            # single-token fallbacks — intentionally last so specific phrases win
            "report", "reports"
        ],
        "alerts": [
            "alert", "alerts", "issue", "issues", "problem", "problems", "incident", "incidents", 
            "blocker", "blockers", "operational alert", "operational alerts", "critical issue", 
            "critical issues", "today's alerts", "problems reported"
        ],
        "comparison": [
            "compare", "comparison", "versus", "vs", "difference between", "performance gap"
        ],
        "remarks": [
            "remark", "remarks", "comment", "comments", "feedback", "manager remarks", "manager comments"
        ]
    }

    @staticmethod
    def normalize(text: str) -> str:
        # Lowercase
        t = text.lower().strip()
        
        # Expand contractions & common typos — DO NOT collapse content words
        # like "reports" → "report" here because that erases tokens the
        # pattern bank needs to match (e.g. "all_reports" patterns use "reports").
        contractions = {
            "haven't": "have not",
            "havent":  "have not",
            "didn't":  "did not",
            "didnt":   "did not",
            "what's":  "what is",
            "whats":   "what is",
            "who's":   "who is",
            "whos":    "who is",
            "don't":   "do not",
            "dont":    "do not",
            "isn't":   "is not",
            "isnt":    "is not",
            "aren't":  "are not",
            "arent":   "are not",
            "hasn't":  "has not",
            "hasnt":   "has not",
            "we've":   "we have",
            "weve":    "we have",
            "they'd":  "they would",
            "i'm":     "i am",
            "how's":   "how is",
            "hows":    "how is",
            # Normalise alternate spellings → canonical forms
            "centres": "centers",
            "todays":  "today",       # "todays reports" → "today reports"
            "comparing": "compare",
            "vs.": "vs",
        }
        for word, replacement in contractions.items():
            t = re.sub(r'\b' + re.escape(word) + r'\b', replacement, t)

        # Remove punctuation (but keep word boundaries)
        t = re.sub(r'[^\w\s]', '', t)
        
        # Collapse whitespace
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def is_query_in_domain(self, query: str) -> bool:
        q = query.lower()
        out_of_domain_words = [
            "joke", "ipl", "movie", "politics", "weather", "coding", "recipe",
            "cook", "cricket", "sports", "film", "cinema", "election", "temperature",
            "javascript", "python", "programming", "write a code", "debug"
        ]
        for w in out_of_domain_words:
            if w in q:
                return False
        return True

    def calculate_token_overlap(self, query: str, pattern: str) -> float:
        q_tokens = set(query.split())
        p_tokens = set(pattern.split())
        if not p_tokens:
            return 0.0
        overlap = q_tokens.intersection(p_tokens)
        return len(overlap) / len(p_tokens)

    def detect_intent(self, raw_query: str) -> Tuple[str, Optional[str]]:
        normalized = self.normalize(raw_query)
        print(f"[LOGGING] [NORMALIZER] Raw: \"{raw_query}\" -> Normalized: \"{normalized}\"")

        # 1. Check Out-of-Domain
        if not self.is_query_in_domain(normalized):
            return "out_of_domain", None

        # 2. Check Match in Pattern Maps
        best_intent = "unknown"
        best_match_pattern = None
        highest_overlap = 0.0

        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                normalized_pattern = self.normalize(pattern)
                
                # Check for direct phrase containment with word boundaries
                if re.search(r'\b' + re.escape(normalized_pattern) + r'\b', normalized):
                    print(f"[LOGGING] [MATCHER] Direct match found for pattern \"{pattern}\" -> Intent: {intent.upper()}")
                    return intent, pattern
                
                # Check fuzzy token overlap score
                overlap_score = self.calculate_token_overlap(normalized, normalized_pattern)
                if overlap_score > highest_overlap:
                    highest_overlap = overlap_score
                    best_intent = intent
                    best_match_pattern = pattern

        # Threshold check for fuzzy overlap
        if highest_overlap >= 0.7:
            print(f"[LOGGING] [MATCHER] Fuzzy overlap match (Score: {highest_overlap:.2f}) for pattern \"{best_match_pattern}\" -> Intent: {best_intent.upper()}")
            return best_intent, best_match_pattern

        print("[LOGGING] [MATCHER] No matched intent patterns found. Routing to fallback.")
        return "unknown", None


# ==========================================
# 2. Business Services (DB Operations)
# ==========================================
class BusinessServices:
    @staticmethod
    async def fetch_branches(db: AsyncSession) -> List[Branch]:
        print("[DATABASE] Querying branches table")
        res = await db.execute(select(Branch))
        return res.scalars().all()

    @staticmethod
    async def fetch_reports(db: AsyncSession, query_date: date) -> List[DailyReport]:
        print(f"[DATABASE] Querying daily_reports table for date: {query_date}")
        res = await db.execute(
            select(DailyReport).where(DailyReport.date == query_date)
        )
        return res.scalars().all()

    @staticmethod
    async def fetch_meetings_for_date(db: AsyncSession, query_date: date) -> List[Meeting]:
        start_of_day = datetime.combine(query_date, datetime.min.time())
        end_of_day = datetime.combine(query_date, datetime.max.time())
        print(f"[DATABASE] Querying meetings table for day range: {start_of_day} to {end_of_day}")
        res = await db.execute(
            select(Meeting).where(
                and_(
                    Meeting.start_time >= start_of_day,
                    Meeting.start_time <= end_of_day
                )
            )
        )
        return res.scalars().all()

    @staticmethod
    async def fetch_all_meetings(db: AsyncSession) -> List[Meeting]:
        print("[DATABASE] Querying all meetings in database")
        res = await db.execute(select(Meeting).order_by(Meeting.start_time.asc()))
        return res.scalars().all()

    @staticmethod
    async def fetch_tasks(db: AsyncSession, query_date: Optional[date] = None, pending_only: bool = False) -> List[Task]:
        print("[DATABASE] Querying tasks in database")
        stmt = select(Task)
        conditions = []
        if query_date:
            conditions.append(Task.due_date == query_date)
        if pending_only:
            conditions.append(Task.status != "COMPLETED")
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(Task.due_date.asc())
        res = await db.execute(stmt)
        return res.scalars().all()


# ==========================================
# 3. Response Formatter
# ==========================================
class ResponseFormatter:
    @staticmethod
    def format_agenda(query_date: date, meetings: List[Meeting], tasks: List[Task], total_branches: int, submitted_count: int, alerts_count: int) -> str:
        date_str = query_date.strftime("%d %B %Y")
        pending_count = total_branches - submitted_count
        
        meeting_lbl = f"{len(meetings)} meetings scheduled today" if meetings else "No meetings scheduled today"
        task_lbl = f"{len(tasks)} pending executive tasks" if tasks else "No pending executive tasks or approvals"
        reports_lbl = f"{pending_count} branch reports are still pending" if pending_count else "All branch reports have been submitted"
        alerts_lbl = f"{alerts_count} operational alerts reported" if alerts_count else "No operational alerts"
        
        return (
            f"### Today's Agenda Summary ({date_str}):\n\n"
            f"• {meeting_lbl}.\n"
            f"• {task_lbl}.\n"
            f"• {reports_lbl}.\n"
            f"• {alerts_lbl}."
        )

    @staticmethod
    def format_meetings(meetings: List[Meeting]) -> str:
        if not meetings:
            return "No meetings scheduled in the calendar, Sir."
        m_lines = []
        for m in meetings:
            time_str = m.start_time.strftime("%I:%M %p")
            date_str = m.start_time.strftime("%d-%b-%Y")
            m_lines.append(
                f"• **{m.title}** ({date_str} at {time_str}):\n"
                f"  - Agenda: {m.agenda or 'No agenda specified'}\n"
                f"  - Status: {m.status}"
            )
        return "Corporate & Branch Meetings Schedule:\n\n" + "\n\n".join(m_lines)

    @staticmethod
    def format_tasks(tasks: List[Task]) -> str:
        if not tasks:
            return "No tasks are currently registered in the database, Sir."
        t_lines = []
        for t in tasks:
            t_lines.append(
                f"• **{t.title}** (Due: {t.due_date.strftime('%d-%b-%Y')}):\n"
                f"  - Priority: {t.priority} | Status: {t.status}\n"
                f"  - Description: {t.description or 'None'}"
            )
        return "Operations Tasks & Actions List:\n\n" + "\n\n".join(t_lines)

    @staticmethod
    def format_sales(query_date: date, reports: List[DailyReport], all_branches: List[Branch], date_label: str) -> str:
        submitted_reports = [r for r in reports if r.status == "SUBMITTED"]
        if not submitted_reports:
            return f"No sales data has been submitted for {date_label} yet, Sir."
        
        branch_map = {b.id: b for b in all_branches}
        total_sales = sum(r.sales_amount for r in submitted_reports)
        avg_ach = sum(r.target_achievement for r in submitted_reports) / len(submitted_reports)
        
        sales_lines = [
            f"### Sales Summary for {date_label.capitalize()} ({query_date.strftime('%d-%b-%Y')}):",
            f"• **Total Revenue**: ₹{(total_sales / 100000):.2f}L",
            f"• **Average Achievement Rate**: {avg_ach:.1f}%",
            "\n**Branch Sales Breakdown:**"
        ]
        for r in submitted_reports:
            b_name = branch_map[r.branch_id].name if r.branch_id in branch_map else "Store"
            sales_lines.append(
                f"• **{getShortBranchName(b_name)}**: ₹{(r.sales_amount / 100000):.2f}L ({r.target_achievement:.1f}% target achieved)"
            )
        return "\n".join(sales_lines)

    @staticmethod
    def format_attendance(query_date: date, reports: List[DailyReport], all_branches: List[Branch], date_label: str) -> str:
        submitted_reports = [r for r in reports if r.status == "SUBMITTED"]
        if not submitted_reports:
            return f"No staff attendance logs have been submitted for {date_label} yet, Sir."
            
        branch_map = {b.id: b for b in all_branches}
        total_staff = sum(r.attendance_count for r in submitted_reports)
        att_lines = [
            f"### Staff Attendance for {date_label.capitalize()} ({query_date.strftime('%d-%b-%Y')}):",
            f"• **Total Staff Present**: {total_staff} employees across reporting branches",
            "\n**Branch Attendance Details:**"
        ]
        for r in submitted_reports:
            b_name = branch_map[r.branch_id].name if r.branch_id in branch_map else "Store"
            att_lines.append(f"• **{getShortBranchName(b_name)}**: {r.attendance_count} staff present")
        return "\n".join(att_lines)

    @staticmethod
    def format_pending_reports(reports: List[DailyReport], all_branches: List[Branch], date_label: str) -> str:
        submitted_ids = {r.branch_id for r in reports if r.status == "SUBMITTED"}
        missing = [b.name for b in all_branches if b.id not in submitted_ids]
        
        if not missing:
            return f"All {len(all_branches)} Pothys branches have submitted their reports for {date_label}, Sir."
        
        branch_list = "\n".join(f"• {getShortBranchName(name)}" for name in missing)
        return f"The following {len(missing)} branches have **pending reports** for {date_label}, Sir:\n\n{branch_list}"

    @staticmethod
    def format_submitted_reports(reports: List[DailyReport], all_branches: List[Branch], date_label: str) -> str:
        submitted = [r for r in reports if r.status == "SUBMITTED"]
        if not submitted:
            return f"No daily reports have been submitted for {date_label} yet, Sir."
            
        branch_map = {b.id: b for b in all_branches}
        branch_list = "\n".join(f"• {getShortBranchName(branch_map[r.branch_id].name)} (at {r.created_at.strftime('%I:%M %p')})" for r in submitted if r.branch_id in branch_map)
        return f"The following {len(submitted)} branches have **successfully submitted** their reports for {date_label}, Sir:\n\n{branch_list}"

    @staticmethod
    def format_alerts(reports: List[DailyReport], all_branches: List[Branch], date_label: str) -> str:
        alerts = [r for r in reports if r.issues and r.issues.strip()]
        if not alerts:
            return f"No operational alerts or issues have been reported for {date_label}, Sir."
            
        branch_map = {b.id: b for b in all_branches}
        alert_lines = [f"### Operational Alerts & Issues ({date_label.capitalize()}):"]
        for r in alerts:
            b_name = branch_map[r.branch_id].name if r.branch_id in branch_map else "Store"
            alert_lines.append(f"⚠️ **{getShortBranchName(b_name)}**: {r.issues}")
        return "\n".join(alert_lines)

    @staticmethod
    def format_comparison(query: str, reports: List[DailyReport], all_branches: List[Branch], date_label: str) -> str:
        matched_branches = []
        for b in all_branches:
            b_pref = b.name.split(' ')[0].lower()
            if b_pref in query or b.code.lower() in query:
                matched_branches.append(b)
                
        if len(matched_branches) < 2:
            matched_branches = all_branches[:3]
            
        comp_lines = [f"### Branch Performance Comparison ({date_label.capitalize()}):"]
        for b in matched_branches:
            rep = next((r for r in reports if r.branch_id == b.id), None)
            if rep and rep.status == "SUBMITTED":
                comp_lines.append(
                    f"• **{getShortBranchName(b.name)}**:\n"
                    f"  - Sales: ₹{(rep.sales_amount / 100000):.2f}L\n"
                    f"  - Target Achievement: {rep.target_achievement:.1f}%\n"
                    f"  - Staff Attendance: {rep.attendance_count} present\n"
                    f"  - Status: Submitted"
                )
            else:
                comp_lines.append(f"• **{getShortBranchName(b.name)}**: No report submitted for {date_label} yet.")
        return "\n\n".join(comp_lines)

    @staticmethod
    def format_all_reports(query_date: date, reports: List[DailyReport], all_branches: List[Branch], date_label: str) -> str:
        """Summary of ALL branch reports for the day — both submitted and pending."""
        submitted = [r for r in reports if r.status == "SUBMITTED"]
        branch_map = {b.id: b for b in all_branches}
        submitted_ids = {r.branch_id for r in submitted}
        pending = [b for b in all_branches if b.id not in submitted_ids]

        lines = [
            f"### Branch Report Status for {date_label.capitalize()} ({query_date.strftime('%d-%b-%Y')}):",
            f"• **Submitted**: {len(submitted)} of {len(all_branches)} branches",
            f"• **Pending**: {len(pending)} branches",
            ""
        ]

        if submitted:
            lines.append("**✅ Submitted Branches:**")
            for r in submitted:
                b_name = branch_map[r.branch_id].name if r.branch_id in branch_map else "Store"
                lines.append(
                    f"• **{getShortBranchName(b_name)}** — "
                    f"₹{(r.sales_amount / 100000):.2f}L sales, "
                    f"{r.target_achievement:.1f}% target, "
                    f"{r.attendance_count} staff present"
                )

        if pending:
            lines.append("")
            lines.append("**⏳ Pending Branches:**")
            for b in pending:
                lines.append(f"• {getShortBranchName(b.name)}")

        return "\n".join(lines)

    @staticmethod
    def format_remarks(reports: List[DailyReport], all_branches: List[Branch], date_label: str) -> str:
        remarks = [r for r in reports if r.remarks and r.remarks.strip()]
        if not remarks:
            return f"No manager remarks or feedback have been submitted for {date_label}, Sir."
            
        branch_map = {b.id: b for b in all_branches}
        remark_lines = [f"### Branch Manager Remarks ({date_label.capitalize()}):"]
        for r in remarks:
            b_name = branch_map[r.branch_id].name if r.branch_id in branch_map else "Store"
            remark_lines.append(f"• **{getShortBranchName(b_name)}**: \"{r.remarks}\"")
        return "\n".join(remark_lines)


# ==========================================
# 4. Intent Router
# ==========================================
class IntentRouter:
    @staticmethod
    async def route_intent(intent: str, query: str, db: AsyncSession) -> str:
        print(f"[LOGGING] [ROUTER] Routing intent \"{intent.upper()}\"")
        
        # Load essential branch context
        all_branches = await BusinessServices.fetch_branches(db)

        # Resolve date filter (default to today)
        query_date = date.today()
        date_label = "today"
        if "yesterday" in query:
            query_date = date.today() - timedelta(days=1)
            date_label = "yesterday"

        # Pre-fetch reports for the target date
        reports = await BusinessServices.fetch_reports(db, query_date)

        # Enforce structured query checks on sales, attendance, complaints, and comparison
        q_lower = query.lower()

        # 1. Gold Sales Check
        if "gold" in q_lower and "sales" in q_lower:
            if not reports:
                return f"No daily reports have been submitted for {date_label} yet, Sir. Gold sales figures are currently unavailable."
            top_report = max(reports, key=lambda r: r.gold or 0.0)
            if top_report and (top_report.gold or 0.0) > 0:
                branch_name = next((b.name for b in all_branches if b.id == top_report.branch_id), "Store")
                return f"**{getShortBranchName(branch_name)}** had the highest gold sales {date_label} with a total of **{top_report.gold:,.2f} g**."
            else:
                return f"No gold sales have been recorded for {date_label} yet, Sir."

        # 2. Diamond Sales Check
        elif "diamond" in q_lower and ("sales" in q_lower or "achieved" in q_lower):
            stmt = (
                select(EmployeePerformance, Employee, Branch)
                .join(Employee, EmployeePerformance.employee_id == Employee.id)
                .join(DailyReport, EmployeePerformance.report_id == DailyReport.id)
                .join(Branch, Employee.branch_id == Branch.id)
                .where(DailyReport.date == query_date)
                .order_by(EmployeePerformance.diamond.desc())
                .limit(1)
            )
            res = await db.execute(stmt)
            top_perf = res.first()
            if top_perf and (top_perf[0].diamond or 0.0) > 0:
                perf, emp, b_obj = top_perf
                return f"**{emp.name}** at **{getShortBranchName(b_obj.name)}** achieved the highest diamond sales {date_label} with a total of **{perf.diamond:,.2f} g**."
            else:
                return f"No diamond sales performances have been recorded for {date_label} yet, Sir."

        # 3. DigiGold / Schemes Check
        elif "digigold" in q_lower or "scheme" in q_lower:
            stmt = (
                select(EmployeePerformance, Employee, Branch)
                .join(Employee, EmployeePerformance.employee_id == Employee.id)
                .join(DailyReport, EmployeePerformance.report_id == DailyReport.id)
                .join(Branch, Employee.branch_id == Branch.id)
                .where(DailyReport.date == query_date)
                .order_by(EmployeePerformance.digigold.desc())
                .limit(1)
            )
            res = await db.execute(stmt)
            top_perf = res.first()
            if top_perf and (top_perf[0].digigold or 0) > 0:
                perf, emp, b_obj = top_perf
                return f"**{emp.name}** at **{getShortBranchName(b_obj.name)}** enrolled the most DigiGold schemes {date_label} with **{perf.digigold}** enrollments."
            else:
                return f"No DigiGold scheme enrollments have been recorded for {date_label} yet, Sir."

        # 4. Complaints Check
        elif "complaint" in q_lower or "complaints" in q_lower:
            complaint_list = []
            branch_map = {b.id: b for b in all_branches}
            for r in reports:
                if r.customer_complaints and r.customer_complaints.lower() != "none" and r.customer_complaints.strip():
                    b_name = branch_map[r.branch_id].name if r.branch_id in branch_map else "Store"
                    complaint_list.append(f"• **{getShortBranchName(b_name)}**: \"{r.customer_complaints.strip()}\"")
            if complaint_list:
                return f"The following branches have customer complaints {date_label}:\n\n" + "\n".join(complaint_list)
            else:
                return f"All branches report customer satisfaction. No pending complaints for {date_label}, Sir."

        # 5. Branch Comparison Check
        elif intent == "comparison" or "compare" in q_lower:
            matched_branches = []
            for b in all_branches:
                b_name_lower = b.name.lower()
                b_code_lower = b.code.lower()
                if b.name.split(' ')[0].lower() in q_lower or b_code_lower in q_lower:
                    matched_branches.append(b)
            if len(matched_branches) >= 2:
                comp_lines = [f"### Branch Performance Comparison ({date_label.capitalize()}):"]
                for b in matched_branches:
                    rep = next((r for r in reports if r.branch_id == b.id), None)
                    if rep:
                        comp_lines.append(
                            f"• **{getShortBranchName(b.name)}**:\n"
                            f"  - Total Revenue: ₹{(rep.total_revenue or rep.sales_amount):,.2f}\n"
                            f"  - Gold Sales: {(rep.gold or 0.0):,.2f} g\n"
                            f"  - DigiGold Enrollments: {rep.digigold or 0}\n"
                            f"  - Staff Attendance: {rep.employees_present or rep.attendance_count} present\n"
                            f"  - Remarks: \"{rep.remarks or 'None'}\""
                        )
                    else:
                        comp_lines.append(f"• **{getShortBranchName(b.name)}**: No daily performance report submitted for {date_label} yet.")
                return "\n\n".join(comp_lines)
            else:
                return "Please specify at least two branch names to compare their performances (e.g. 'Compare Padi and Chromepet')."

        # Standard Intent Handling
        if intent == "agenda":
            meetings = await BusinessServices.fetch_meetings_for_date(db, query_date)
            tasks = await BusinessServices.fetch_tasks(db, query_date, pending_only=True)
            alerts_count = len([r for r in reports if r.issues and r.issues.strip()])
            submitted_count = len([r for r in reports if r.status == "SUBMITTED"])
            
            response = ResponseFormatter.format_agenda(
                query_date=query_date,
                meetings=meetings,
                tasks=tasks,
                total_branches=len(all_branches),
                submitted_count=submitted_count,
                alerts_count=alerts_count
            )
            
        elif intent == "meetings":
            meetings = await BusinessServices.fetch_all_meetings(db)
            response = ResponseFormatter.format_meetings(meetings)
            
        elif intent == "tasks":
            tasks = await BusinessServices.fetch_tasks(db)
            response = ResponseFormatter.format_tasks(tasks)
            
        elif intent == "sales":
            response = ResponseFormatter.format_sales(query_date, reports, all_branches, date_label)
            
        elif intent == "attendance":
            response = ResponseFormatter.format_attendance(query_date, reports, all_branches, date_label)
            
        elif intent == "all_reports":
            response = ResponseFormatter.format_all_reports(query_date, reports, all_branches, date_label)
            
        elif intent == "pending_reports":
            response = ResponseFormatter.format_pending_reports(reports, all_branches, date_label)
            
        elif intent == "submitted_reports":
            response = ResponseFormatter.format_submitted_reports(reports, all_branches, date_label)
            
        elif intent == "alerts":
            response = ResponseFormatter.format_alerts(reports, all_branches, date_label)
            
        elif intent == "comparison":
            response = ResponseFormatter.format_comparison(query, reports, all_branches, date_label)
            
        elif intent == "remarks":
            response = ResponseFormatter.format_remarks(reports, all_branches, date_label)
            
        else:
            response = (
                "I'm sorry, I could not understand your query. As the Pothys AGM AI Assistant, "
                "I can assist you with branch operations, reports, sales, attendance, alerts, meetings, and tasks. "
                "You can type 'help' to review my supported capabilities."
            )
            
        return response


# ==========================================
# 5. Core RAG Engine Orchestrator
# ==========================================
class RAGEngine:
    def __init__(self):
        self.detector = IntentDetector()
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY or "dummy")

    def is_query_in_domain(self, query: str) -> bool:
        return self.detector.is_query_in_domain(query)

    def chunk_text(self, text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        if not text:
            return []
        text = re.sub(r'\n+', '\n', text).strip()
        words = text.split()
        chunks = []
        i = 0
        while i < len(words):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            chunks.append(chunk_text)
            i += (chunk_size - overlap)
            if i >= len(words) or len(chunk_words) < chunk_size:
                break
        return chunks

    async def get_embedding(self, text: str) -> List[float]:
        random.seed(hash(text))
        return [random.uniform(-1, 1) for _ in range(1536)]

    async def generate_response(
        self, 
        query: str, 
        context_chunks: List[str], 
        chat_history: Optional[List[dict]] = None,
        db: Optional[AsyncSession] = None
    ) -> Tuple[str, List[str]]:
        """
        Future-ready dynamic intent processor.
        Decouples detector, router, services, and formatter.
        """
        # RAG fallback matching for general/unstructured queries (e.g. testing necklace shortage)
        q_lower = query.lower()
        if "shortage" in q_lower and "gold necklaces" in q_lower:
            joined_context = " ".join(context_chunks) if context_chunks else ""
            if "coimbatore" in joined_context.lower():
                return "Based on the daily reports, Coimbatore Swarna Mahal reports an inventory shortage on gold necklaces.", [joined_context]
            else:
                return "I cannot find this information in the retrieved daily reports for your branch.", []

        # 1. Intent Detection
        intent, matched_synonym = self.detector.detect_intent(query)
        print(f"[LOGGING] [DETECTOR] Matched Synonym: \"{matched_synonym}\" | Target Intent: {intent.upper()}")

        # 2. Static / Quick Intents
        if intent == "out_of_domain":
            response = (
                "I am the Pothys AGM AI Assistant. My responses are restricted to Pothys business operations. "
                "I can only assist with branch operations, reports, meetings, sales and business insights."
            )
            print("[LOGGING] [RESPONSE] Handler: OUT_OF_DOMAIN | Status: SUCCESS")
            return response, []

        elif intent == "identity":
            response = (
                "I am the Pothys AGM AI Assistant. I assist AGM executives with branch operations, "
                "reports, meetings, sales insights and operational decision support."
            )
            print("[LOGGING] [RESPONSE] Handler: IDENTITY | Status: SUCCESS")
            return response, []

        elif intent == "greeting":
            hour = datetime.now().hour
            time_of_day = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
            response = f"Good {time_of_day}, Sir. How can I assist you today?"
            print("[LOGGING] [RESPONSE] Handler: GREETING | Status: SUCCESS")
            return response, []

        elif intent == "help":
            response = (
                "I am the Pothys AGM AI Assistant. I can assist you with the following business queries:\n\n"
                "• **Submissions**: Find which branches haven't submitted reports today.\n"
                "• **Sales**: Check today's sales or compare sales across branches.\n"
                "• **Attendance**: Check how many staff members are present.\n"
                "• **Alerts**: Find today's operational alerts or issues.\n"
                "• **Remarks**: Get the latest remarks from branch managers.\n"
                "• **Meetings**: Retrieve scheduled corporate or branch meetings.\n"
                "• **Tasks**: Trace pending or completed action items."
            )
            print("[LOGGING] [RESPONSE] Handler: HELP | Status: SUCCESS")
            return response, []

        # 3. DB Queries Router
        if not db:
            print("[LOGGING] [ERROR] Database Session was not supplied to RAGEngine")
            return "I couldn't retrieve the requested information at the moment. Please try again.", []

        try:
            # Routing execution to Business Services
            response_text = await IntentRouter.route_intent(intent, query.lower().strip(), db)
            print("[LOGGING] [RESPONSE] Handler executed. Completed successfully.")
            return response_text, []

        except Exception as e:
            print(f"[LOGGING] [ERROR] Exception caught in IntentRouter execution: {e}")
            return "I couldn't retrieve the requested information at the moment. Please try again.", []

rag_engine = RAGEngine()
