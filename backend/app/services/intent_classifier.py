"""
Intent Classifier & Slot Extraction Engine for Pothys AGM AI Executive Assistant.

Decomposes every user query into structured slots:
  - intent
  - category (BUSINESS | KNOWLEDGE | STATIC)
  - branch (single branch or primary branch)
  - branches (list of detected branches for comparison)
  - metric (attendance, gold_sales, silver_sales, total_revenue, complaints, etc.)
  - time (today | yesterday)
  - comparison (boolean)
  - aggregation (boolean)
"""

import re
import difflib
from dataclasses import dataclass, field
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime


class IntentCategory:
    BUSINESS = "BUSINESS"
    KNOWLEDGE = "KNOWLEDGE"
    STATIC = "STATIC"


class BusinessIntent:
    BRANCH_METRIC = "BRANCH_METRIC"          # Specific metric for specific branch e.g. "Attendance in Poonamallee"
    BRANCH_REPORT = "BRANCH_REPORT"          # Full branch report e.g. "Poonamallee report"
    COMPARE_BRANCHES = "COMPARE_BRANCHES"    # Compare 2+ branches e.g. "Compare Padi and Poonamallee"
    TOTAL_ABSENTEES = "TOTAL_ABSENTEES"      # Total absentees aggregate e.g. "Total absent today"
    ATTENDANCE = "ATTENDANCE"               # Attendance intent
    TOTAL_REVENUE = "TOTAL_REVENUE"          # Total revenue aggregate e.g. "Total revenue today"
    TODAY_REVENUE = "TOTAL_REVENUE"          # Alias for TOTAL_REVENUE
    TOTAL_METRIC = "TOTAL_METRIC"            # Total aggregate for a specific metric e.g. "Total silver sales"
    TOP_PERFORMER = "TOP_PERFORMER"          # "Highest performing executive"
    TOP_BRANCH = "TOP_BRANCH"               # "Highest revenue today"
    REPORT_STATUS = "REPORT_STATUS"          # "Today's reports"
    PENDING_REPORTS = "PENDING_REPORTS"      # "Pending reports"
    SUBMITTED_REPORTS = "SUBMITTED_REPORTS"  # "Submitted reports"
    ALERTS = "ALERTS"                       # "Operational alerts"
    COMPLAINTS = "COMPLAINTS"               # "Customer complaints"
    REMARKS = "REMARKS"                     # "Manager remarks"
    COMPARISON = "COMPARISON"               # Alias for COMPARE_BRANCHES
    DIGIGOLD = "DIGIGOLD"                   # "DigiGold enrollments"
    GOLD_SALES = "GOLD_SALES"              # "Gold sales today"
    DIAMOND_SALES = "DIAMOND_SALES"         # "Diamond sales"
    AGENDA = "AGENDA"                       # "Today's agenda"
    MEETINGS = "MEETINGS"                   # "Upcoming meetings"
    TASKS = "TASKS"                         # "Pending tasks"
    
    # New intents
    GET_BRANCH_REPORT = "GET_BRANCH_REPORT"
    GET_BRANCH_REVENUE = "GET_BRANCH_REVENUE"
    GET_GOLD_SALES = "GET_GOLD_SALES"
    GET_SILVER_SALES = "GET_SILVER_SALES"
    GET_ATTENDANCE = "GET_ATTENDANCE"
    GET_PENDING_REPORTS = "GET_PENDING_REPORTS"
    GET_TOP_BRANCH = "GET_TOP_BRANCH"
    GET_TOP_EXECUTIVE = "GET_TOP_EXECUTIVE"
    CREATE_MEETING = "CREATE_MEETING"
    UPDATE_MEETING = "UPDATE_MEETING"
    DELETE_MEETING = "DELETE_MEETING"
    SHOW_TODAYS_AGENDA = "SHOW_TODAYS_AGENDA"
    SHOW_ALERTS = "SHOW_ALERTS"
    SHOW_COMPLAINTS = "SHOW_COMPLAINTS"
    SHOW_OPERATIONAL_ISSUES = "SHOW_OPERATIONAL_ISSUES"


class StaticIntent:
    GREETING = "GREETING"
    HELP = "HELP"
    IDENTITY = "IDENTITY"
    ACKNOWLEDGMENT = "ACKNOWLEDGMENT"
    OUT_OF_DOMAIN = "OUT_OF_DOMAIN"


@dataclass
class QuerySlots:
    intent: str
    category: str
    branch: Optional[str] = None
    branches: List[str] = field(default_factory=list)
    metric: Optional[str] = None
    time: str = "today"
    comparison: bool = False
    aggregation: bool = False
    metrics: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "category": self.category,
            "branch": self.branch,
            "branches": self.branches,
            "metric": self.metric,
            "time": self.time,
            "comparison": self.comparison,
            "aggregation": self.aggregation,
            "metrics": self.metrics,
        }


# ─────────────────────────────────────────────
# Branch Alias & Fuzzy Matching Dictionary
# ─────────────────────────────────────────────

BRANCH_ALIASES: Dict[str, List[str]] = {
    "padi": ["padi", "paadi", "paddi", "padi branch", "padi store", "padi swarna mahal"],
    "chromepet": ["chromepet", "chrompet", "chromepett", "chromepet branch", "chromepet store", "chromepet swarna mahal"],
    "poonamallee": ["poonamallee", "poonamalle", "ponamallee", "punamallee", "poonamallee branch", "poonamallee store", "poonamallee swarna mahal"],
    "coimbatore": ["coimbatore", "coimbatore branch", "kovai", "cbe", "coimbatore store"],
    "salem": ["salem", "salem branch", "salem store"],
    "trichy": ["trichy", "trichi", "tiruchirappalli", "trichy branch", "trichy store"],
    "tirunelveli": ["tirunelveli", "tirunelveli branch", "nellai", "tirunelveli store"],
    "trivandrum": ["trivandrum", "thiruvananthapuram", "trivandrum branch", "trivandrum store", "thiruvananthapuram branch"],
}

CANONICAL_BRANCH_NAMES: Dict[str, str] = {
    "padi": "Padi",
    "chromepet": "Chromepet",
    "poonamallee": "Poonamallee",
    "coimbatore": "Coimbatore",
    "salem": "Salem",
    "trichy": "Trichy",
    "tirunelveli": "Tirunelveli",
    "trivandrum": "Trivandrum",
}


def extract_branch_name(query: str) -> Optional[str]:
    """Backward compatibility helper. Returns primary branch name or None."""
    branches = extract_branches_fuzzy(query)
    return branches[0] if branches else None

BRANCH_KEYWORDS = CANONICAL_BRANCH_NAMES

COMMON_QUERY_WORDS = {
    "today", "yesterday", "report", "reports", "total", "sales", "store",
    "stores", "branch", "branches", "staff", "gross", "overall", "present",
    "absent", "complaint", "complaints", "issue", "issues", "remark", "remarks",
    "give", "show", "what", "which", "how", "many", "much", "best", "top", "list"
}


def extract_branches_fuzzy(query: str) -> List[str]:
    """
    Extract all branch names from query using phrase matching and token fuzzy matching.
    Returns list of canonical branch names maintaining query appearance order.
    """
    norm_q = query.lower().strip()
    norm_q_clean = re.sub(r'[^\w\s]', ' ', norm_q)
    tokens = norm_q_clean.split()

    found_keys = set()

    # 1. Exact alias / phrase matching
    for key, aliases in BRANCH_ALIASES.items():
        for alias in aliases:
            norm_alias = alias.lower()
            if re.search(r'\b' + re.escape(norm_alias) + r'\b', norm_q) or norm_alias in norm_q:
                found_keys.add(key)
                break

    # 2. Token fuzzy matching for misspelled single words (e.g. 'chrompet', 'poonamale')
    if not found_keys:
        all_alias_words = []
        word_to_key = {}
        for key, aliases in BRANCH_ALIASES.items():
            for alias in aliases:
                for word in alias.split():
                    if len(word) >= 4 and word not in COMMON_QUERY_WORDS:
                        all_alias_words.append(word)
                        word_to_key[word] = key

        for token in tokens:
            if len(token) >= 4 and token not in COMMON_QUERY_WORDS:
                matches = difflib.get_close_matches(token, all_alias_words, n=1, cutoff=0.8)
                if matches:
                    matched_word = matches[0]
                    found_keys.add(word_to_key[matched_word])

    # Convert keys to canonical names maintaining query order
    result = []
    for key in BRANCH_ALIASES.keys():
        if key in found_keys:
            result.append(CANONICAL_BRANCH_NAMES[key])

    return result


def extract_date_context(query: str) -> str:
    """Extract date context from query. Returns 'today' or 'yesterday'."""
    q = query.lower()
    if "yesterday" in q:
        return "yesterday"
    return "today"


# ─────────────────────────────────────────────
# Metric Recognition & Synonyms
# ─────────────────────────────────────────────

METRIC_SYNONYMS: Dict[str, List[str]] = {
    "gold_sales": [
        "gold sales", "gold revenue", "gold amount", "gold sales volume",
        "gold turnover", "gold", "gold pieces", "gold value"
    ],
    "silver_sales": [
        "silver sales", "silver revenue", "silver amount", "silver sales volume",
        "silver turnover", "silver", "silver value"
    ],
    "platinum_sales": [
        "platinum sales", "platinum revenue", "platinum amount", "platinum", "platinum value"
    ],
    "diamond_sales": [
        "diamond sales", "diamond revenue", "diamond amount", "diamond", "diamond value"
    ],
    "attendance": [
        "attendance", "staff attendance", "headcount", "manpower",
        "present", "employees present", "who is present", "staff present",
        "absent", "absentees", "total absentees", "employees absent",
        "staff absent", "who is absent", "absentee count"
    ],
    "total_revenue": [
        "total revenue", "overall revenue", "gross revenue", "today revenue",
        "today sales", "total sales", "turnover", "sales amount", "gross sales",
        "revenue", "sales", "business"
    ],
    "complaints": [
        "complaint", "complaints", "customer complaint", "customer complaints",
        "customer issues", "customer feedback"
    ],
    "issues": [
        "issue", "issues", "operational issue", "operational issues",
        "operational alert", "operational alerts", "alerts", "problem", "problems"
    ],
    "remarks": [
        "remark", "remarks", "manager remark", "manager remarks",
        "manager comment", "comments", "feedback"
    ],
    "digigold": [
        "digigold", "digi gold", "digisilver", "digi silver",
        "scheme enrollment", "scheme enrollments", "digital scheme", "schemes"
    ]
}


def extract_metric(query: str) -> Optional[str]:
    """Extract metric slot from user query using synonym matching."""
    norm_q = query.lower().strip()

    for metric_name, synonyms in METRIC_SYNONYMS.items():
        for syn in synonyms:
            if re.search(r'\b' + re.escape(syn) + r'\b', norm_q):
                return metric_name

    return None


STATIC_PATTERNS = {
    StaticIntent.IDENTITY: [
        "who are you", "what is your name", "introduce yourself",
        "your name", "who you are", "identity",
    ],
    StaticIntent.GREETING: [
        "hi", "hello", "hey", "good morning", "good afternoon",
        "good evening", "greetings",
    ],
    StaticIntent.HELP: [
        "help", "what can you do", "capabilities", "features",
        "how to use", "commands", "menu",
    ],
    StaticIntent.ACKNOWLEDGMENT: [
        "okay", "ok", "done", "thanks", "thank you", "got it", "alright",
        "cool", "nice", "great", "good", "superb", "perfect", "wonderful",
        "fine", "noted", "understood", "sure", "yes", "yeah", "yep",
    ],
}

KNOWLEDGE_KEYWORDS = [
    "sop", "standard operating procedure", "policy", "policies",
    "manual", "handbook", "hr document", "training document",
    "company policy", "employee handbook", "guidelines",
    "shortage", "necklace", "necklaces", "audit", "document",
]

OUT_OF_DOMAIN_KEYWORDS = [
    "joke", "ipl", "movie", "politics", "weather", "coding", "recipe",
    "cook", "cricket", "sports", "film", "cinema", "election",
    "javascript", "python", "programming", "write a code", "debug",
]


def normalize_query(text: str) -> str:
    """Normalize user input for pattern matching."""
    t = text.lower().strip()

    contractions = {
        "haven't": "have not", "havent": "have not",
        "didn't": "did not", "didnt": "did not",
        "what's": "what is", "whats": "what is",
        "who's": "who is", "whos": "who is",
        "don't": "do not", "dont": "do not",
        "isn't": "is not", "isnt": "is not",
        "aren't": "are not", "arent": "are not",
        "hasn't": "has not", "hasnt": "has not",
        "today's": "today", "todays": "today",
        "centres": "centers",
        "comparing": "compare",
        "vs.": "vs",
    }
    for word, replacement in contractions.items():
        t = re.sub(r'\b' + re.escape(word) + r'\b', replacement, t)

    t = re.sub(r'[^\w\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


class IntentClassifier:
    """
    Classifies user queries and extracts structured slots.
    """

    def classify_slots(self, raw_query: str) -> QuerySlots:
        norm = normalize_query(raw_query)
        time_ctx = extract_date_context(norm)
        branches = extract_branches_fuzzy(norm)
        primary_branch = branches[0] if branches else None
        metric = extract_metric(norm)

        # 1. Out of domain check
        for keyword in OUT_OF_DOMAIN_KEYWORDS:
            if keyword in norm:
                return QuerySlots(
                    intent=StaticIntent.OUT_OF_DOMAIN,
                    category=IntentCategory.STATIC,
                    time=time_ctx
                )

        # 1b. Short acknowledgment check — only fire if the ENTIRE query is casual
        ACKNOWLEDGMENT_WORDS = {
            "okay", "ok", "done", "thanks", "thank you", "got it", "alright",
            "cool", "nice", "great", "good", "superb", "perfect", "wonderful",
            "fine", "noted", "understood", "sure", "yes", "yeah", "yep", "no",
            "nope", "nah", "bye", "goodbye", "see you", "see ya",
        }
        if norm in ACKNOWLEDGMENT_WORDS:
            return QuerySlots(
                intent=StaticIntent.ACKNOWLEDGMENT,
                category=IntentCategory.STATIC,
                time=time_ctx
            )

        # 2. Static intents
        for intent, patterns in STATIC_PATTERNS.items():
            if intent == StaticIntent.ACKNOWLEDGMENT:
                continue  # already handled above
            for pattern in patterns:
                norm_p = normalize_query(pattern)
                if re.search(r'\b' + re.escape(norm_p) + r'\b', norm):
                    return QuerySlots(
                        intent=intent,
                        category=IntentCategory.STATIC,
                        time=time_ctx
                    )

        # 3. Knowledge / RAG check
        for keyword in KNOWLEDGE_KEYWORDS:
            if keyword in norm:
                return QuerySlots(
                    intent="DOCUMENT_QUERY",
                    category=IntentCategory.KNOWLEDGE,
                    time=time_ctx
                )

        # 4. Business intent classification based on extracted slots
        
        # A. Meeting creation, updating, deletion (Highest priority)
        if any(w in norm for w in ["schedule my agenda", "create a meeting", "arrange a meeting", "schedule a meeting", "book a meeting", "set up a meeting"]):
            return QuerySlots(intent=BusinessIntent.CREATE_MEETING, category=IntentCategory.BUSINESS, time=time_ctx)
        
        if any(w in norm for w in ["update meeting", "change meeting", "reschedule meeting", "edit meeting"]):
            return QuerySlots(intent=BusinessIntent.UPDATE_MEETING, category=IntentCategory.BUSINESS, time=time_ctx)
            
        if any(w in norm for w in ["delete meeting", "cancel meeting", "remove meeting"]):
            return QuerySlots(intent=BusinessIntent.DELETE_MEETING, category=IntentCategory.BUSINESS, time=time_ctx)

        # B. Comparison
        if len(branches) >= 2 or any(w in norm for w in ["compare", "comparison", "versus", "vs", "difference between", "contrast", "contrasting"]):
            return QuerySlots(
                intent=BusinessIntent.COMPARE_BRANCHES,
                category=IntentCategory.BUSINESS,
                branch=primary_branch,
                branches=branches,
                metric=metric,
                time=time_ctx,
                comparison=True
            )

        # C. Branch Specific Queries
        if primary_branch:
            if metric:
                return QuerySlots(
                    intent=BusinessIntent.BRANCH_METRIC,
                    category=IntentCategory.BUSINESS,
                    branch=primary_branch,
                    branches=branches,
                    metric=metric,
                    time=time_ctx
                )
            else:
                return QuerySlots(
                    intent=BusinessIntent.BRANCH_REPORT,
                    category=IntentCategory.BUSINESS,
                    branch=primary_branch,
                    branches=branches,
                    time=time_ctx
                )

        # D. Non-branch queries by phrase / pattern
        if any(w in norm for w in ["pending report", "pending reports", "missing report", "not submitted", "yet to submit", "unsubmitted"]):
            return QuerySlots(intent=BusinessIntent.PENDING_REPORTS, category=IntentCategory.BUSINESS, time=time_ctx)

        if any(w in norm for w in ["submitted report", "submitted reports", "who submitted", "submissions today", "branches submitted", "which branches submitted", "branches that submitted"]):
            return QuerySlots(intent=BusinessIntent.SUBMITTED_REPORTS, category=IntentCategory.BUSINESS, time=time_ctx)

        if any(w in norm for w in ["highest revenue", "top branch", "best branch", "leading branch", "which branch is leading", "most revenue", "best performing branch", "top performing branch", "leading store"]):
            return QuerySlots(intent=BusinessIntent.TOP_BRANCH, category=IntentCategory.BUSINESS, time=time_ctx)

        if any(w in norm for w in ["best performer", "top performer", "highest performing executive", "best employee", "top employee", "best salesperson", "top salesperson", "best performing employee"]):
            return QuerySlots(intent=BusinessIntent.TOP_PERFORMER, category=IntentCategory.BUSINESS, time=time_ctx)

        # E. Aggregate queries by metric
        if metric:
            if metric == "attendance":
                if any(w in norm for w in ["absent", "absentees", "absent staff", "staff absent", "absentee count"]):
                    return QuerySlots(intent=BusinessIntent.TOTAL_ABSENTEES, category=IntentCategory.BUSINESS, metric=metric, time=time_ctx, aggregation=True)
                return QuerySlots(intent=BusinessIntent.ATTENDANCE, category=IntentCategory.BUSINESS, metric=metric, time=time_ctx, aggregation=True)
            elif metric == "total_revenue":
                return QuerySlots(intent=BusinessIntent.TOTAL_REVENUE, category=IntentCategory.BUSINESS, metric=metric, time=time_ctx, aggregation=True)
            elif metric == "gold_sales":
                return QuerySlots(intent=BusinessIntent.GOLD_SALES, category=IntentCategory.BUSINESS, metric=metric, time=time_ctx, aggregation=True)
            elif metric == "diamond_sales":
                return QuerySlots(intent=BusinessIntent.DIAMOND_SALES, category=IntentCategory.BUSINESS, metric=metric, time=time_ctx, aggregation=True)
            elif metric == "silver_sales":
                return QuerySlots(intent=BusinessIntent.TOTAL_METRIC, category=IntentCategory.BUSINESS, metric=metric, time=time_ctx, aggregation=True)
            elif metric == "complaints":
                return QuerySlots(intent=BusinessIntent.COMPLAINTS, category=IntentCategory.BUSINESS, metric=metric, time=time_ctx, aggregation=True)
            elif metric == "issues":
                return QuerySlots(intent=BusinessIntent.SHOW_OPERATIONAL_ISSUES, category=IntentCategory.BUSINESS, metric=metric, time=time_ctx, aggregation=True)
            elif metric == "remarks":
                return QuerySlots(intent=BusinessIntent.REMARKS, category=IntentCategory.BUSINESS, metric=metric, time=time_ctx, aggregation=True)
            elif metric == "digigold":
                return QuerySlots(intent=BusinessIntent.DIGIGOLD, category=IntentCategory.BUSINESS, metric=metric, time=time_ctx, aggregation=True)
            else:
                return QuerySlots(intent=BusinessIntent.TOTAL_METRIC, category=IntentCategory.BUSINESS, metric=metric, time=time_ctx, aggregation=True)

        if any(w in norm for w in ["agenda", "schedule today", "executive agenda"]):
            return QuerySlots(intent=BusinessIntent.AGENDA, category=IntentCategory.BUSINESS, time=time_ctx)

        if any(w in norm for w in ["meeting", "meetings", "appointment", "calendar"]):
            return QuerySlots(intent=BusinessIntent.MEETINGS, category=IntentCategory.BUSINESS, time=time_ctx)

        if any(w in norm for w in ["task", "tasks", "action item", "todo"]):
            return QuerySlots(intent=BusinessIntent.TASKS, category=IntentCategory.BUSINESS, time=time_ctx)

        # Fallback
        return QuerySlots(intent=BusinessIntent.REPORT_STATUS, category=IntentCategory.BUSINESS, time=time_ctx)

    def classify(self, raw_query: str) -> Tuple[str, str, Optional[str]]:
        """
        Legacy interface compatibility. Returns (category, intent, primary_branch).
        """
        slots = self.classify_slots(raw_query)
        print(f"[INTENT_CLASSIFIER] Slots: {slots.to_dict()}")
        return slots.category, slots.intent, slots.branch

    async def classify_slots_async(self, raw_query: str) -> QuerySlots:
        # Short casual phrases — skip Groq entirely, use local classifier
        norm = raw_query.lower().strip()
        CASUAL_ONLY = {
            "okay", "ok", "done", "thanks", "thank you", "got it", "alright",
            "cool", "nice", "great", "good", "superb", "perfect", "wonderful",
            "fine", "noted", "understood", "sure", "yes", "yeah", "yep", "no",
            "nope", "nah", "bye", "goodbye", "see you", "see ya",
        }
        if norm in CASUAL_ONLY:
            return self.classify_slots(raw_query)

        from app.services.gemini_service import gemini_service
        try:
            res_dict = await gemini_service.extract_query_slots(raw_query)
            if res_dict:
                category = res_dict.get("category", IntentCategory.BUSINESS)
                intent = res_dict.get("intent", BusinessIntent.REPORT_STATUS)

                # If Groq says OUT_OF_DOMAIN, cross-check with local classifier
                # which reliably detects business keywords (branch names, metrics, etc.)
                if intent == StaticIntent.OUT_OF_DOMAIN:
                    local_slots = self.classify_slots(raw_query)
                    if local_slots.category == IntentCategory.BUSINESS:
                        print(f"[INTENT_CLASSIFIER] Groq returned OUT_OF_DOMAIN but local classifier detected business intent: {local_slots.intent}")
                        return local_slots

                branches = res_dict.get("branches", [])
                primary_branch = branches[0] if branches else None
                metrics = res_dict.get("metrics", [])
                metric = metrics[0] if metrics else None
                time_ctx = res_dict.get("time", "today")
                comparison = intent == "COMPARE_BRANCHES" or len(branches) >= 2
                aggregation = len(branches) == 0 and intent not in ["CREATE_MEETING", "UPDATE_MEETING", "DELETE_MEETING", "SHOW_TODAYS_AGENDA"]
                
                return QuerySlots(
                    intent=intent,
                    category=category,
                    branch=primary_branch,
                    branches=branches,
                    metric=metric,
                    time=time_ctx,
                    comparison=comparison,
                    aggregation=aggregation,
                    metrics=metrics
                )
        except Exception as e:
            print(f"[INTENT_CLASSIFIER] Gemini slot extraction failed, falling back to local patterns: {e}")

        return self.classify_slots(raw_query)

    async def classify_async(self, raw_query: str) -> Tuple[str, str, Optional[str]]:
        slots = await self.classify_slots_async(raw_query)
        print(f"[INTENT_CLASSIFIER] Slots (Async): {slots.to_dict()}")
        return slots.category, slots.intent, slots.branch


intent_classifier = IntentClassifier()
