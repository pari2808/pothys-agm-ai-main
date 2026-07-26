import re
from difflib import SequenceMatcher
from typing import Optional, Any

def normalize_text(text: Any) -> str:
    """Clean string by lowercasing, stripping punctuation and collapsing whitespace."""
    if text is None:
        return ""
    s = str(text).lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def match_alias(cell_value: Any, aliases: list[str], threshold: float = 0.82) -> float:
    """
    Check if a cell value matches any alias in the list.
    Returns similarity score between 0.0 and 1.0 (1.0 = exact match).
    """
    val_norm = normalize_text(cell_value)
    if not val_norm:
        return 0.0

    best_score = 0.0
    for alias in aliases:
        alias_norm = normalize_text(alias)
        if not alias_norm:
            continue

        if val_norm == alias_norm:
            return 1.0

        # Inline key-value check: val_norm stripped of trailing digits/delimiters equals alias_norm
        # e.g., val_norm="employees on leave 2" -> val_clean="employees on leave" == alias_norm
        val_clean = re.sub(r"[\d:\-=\s]+$", "", val_norm).strip()
        if val_clean and val_clean == alias_norm:
            return 0.98
        
        # Word boundary contained check: alias phrase is fully contained within cell label
        if re.search(rf"\b{re.escape(alias_norm)}\b", val_norm):
            # Guard against "manager remarks" matching alias "manager"
            if alias_norm in ["manager", "manager name", "bm name", "branch manager", "bm", "store manager"] and re.search(r"\b(remarks?|issues?|complaints?|sub|assistant|deputy)\b", val_norm):
                continue
            # Guard against "overall remarks" / "scheme remarks" matching "remarks"
            if alias_norm == "remarks" and re.search(r"\b(overall|scheme)\b", val_norm):
                continue
            # Guard against "customer complaints" matching "operational issues" or vice versa
            if alias_norm in ["customer complaints", "complaints"] and re.search(r"\b(operational|issues?)\b", val_norm):
                continue
            if alias_norm in ["operational issues", "operational issue", "issues"] and re.search(r"\b(customer|complaints?)\b", val_norm):
                continue
            # Guard against metadata name labels (Manager Name, Branch Name) matching employee table name column
            if alias_norm in ["name", "employee name", "emp name", "staff name"] and re.search(r"\b(manager|branch|store|location|sub manager|assistant manager)\b", val_norm):
                continue
            score = 0.90
            if score > best_score:
                best_score = score

        # Sequence matcher fuzzy match
        ratio = SequenceMatcher(None, val_norm, alias_norm).ratio()
        if ratio > best_score:
            best_score = ratio

    return best_score if best_score >= threshold else 0.0


# ---------------------------------------------------------------------------
# Metadata / Branch-level scalar fields (extracted via AnchorParser)
# ---------------------------------------------------------------------------

FIELD_MAPPINGS = {
    "report_date": {
        "aliases": ["report date", "date", "tx date", "transaction date", "daily date", "report dt", "as of date"],
        "type": "date",
        "default": None
    },
    "branch_name": {
        "aliases": ["branch name", "branch", "location", "showroom", "store", "store name", "branch location"],
        "type": "string",
        "default": "Unknown Branch"
    },
    "manager_name": {
        "aliases": ["manager name", "manager", "bm name", "branch manager", "bm", "store manager"],
        "type": "string",
        "default": "Unknown Manager"
    },
    "sub_manager_name": {
        "aliases": ["sub manager name", "sub manager", "assistant manager", "assistant branch manager", "abm", "deputy manager"],
        "type": "string",
        "default": "None"
    },

    "gold_weight": {
        "aliases": ["gold weight", "gold grams", "gold gms", "gold weight g", "gold (grams)", "gold g", "gold wt", "gold"],
        "type": "string",
        "default": None
    },
    "diamond_weight": {
        "aliases": ["diamond weight", "diamond grams", "diamond gms", "diamond cts", "diamond weight cts", "diamond carats", "diamond (grams)", "diamond (cts)", "diamond g", "diamond wt", "diamond"],
        "type": "string",
        "default": None
    },
    "platinum_weight": {
        "aliases": ["platinum weight", "platinum grams", "platinum gms", "platinum weight g", "platinum (grams)", "platinum g", "platinum wt", "platinum"],
        "type": "string",
        "default": None
    },
    "silver_weight": {
        "aliases": ["silver weight", "silver grams", "silver gms", "silver weight g", "silver (grams)", "silver g", "silver wt", "silver"],
        "type": "string",
        "default": None
    },
    "silver_mrp": {
        "aliases": ["silver mrp", "silver mrp value", "silver mrp (inr)", "silver mrp (rs)", "silver mrp sales", "silver mrp amount"],
        "type": "string",
        "default": None
    },

    # ── Category Revenue Breakdown ──
    "gold_sales": {
        "aliases": [
            "gold sales amount", "gold sales", "gold sale", "gold amount", "today s gold", 
            "gold value", "total gold sales", "gold rs", "gold", "gold business", "gold revenue", 
            "gold collection", "today s gold collection", "today's gold", "gold collection amount",
            "gold turnover", "gold dept sales", "gold section sales", "gold billing", "gold counter sales"
        ],
        "type": "float",
        "default": 0.0
    },
    "silver_sales": {
        "aliases": [
            "silver sales amount", "silver sales", "silver sale", "silver amount", "today s silver", 
            "silver value", "total silver sales", "silver rs", "silver", "silver business", "silver revenue", 
            "silver collection", "today s silver revenue", "today's silver", "silver collection amount",
            "silver turnover", "silver dept sales", "silver section sales", "silver billing"
        ],
        "type": "float",
        "default": 0.0
    },
    "platinum_sales": {
        "aliases": [
            "platinum sales amount", "platinum sales", "platinum sale", "platinum amount", "today s platinum", 
            "platinum value", "platinum rs", "platinum", "platinum business", "platinum revenue", 
            "plat sales", "plat amount", "plat revenue", "today's platinum", "platinum collection",
            "platinum turnover", "platinum dept sales", "platinum section sales", "platinum billing"
        ],
        "type": "float",
        "default": 0.0
    },
    "diamond_sales": {
        "aliases": [
            "diamond sales amount", "diamond sales", "diamond sale", "diamond amount", "today s diamond", 
            "diamond value", "diamond rs", "diamond", "diamond revenue", "diamond business", 
            "dia sales", "dia amount", "dia revenue", "today's diamond", "diamond collection",
            "diamond turnover", "diamond dept sales", "diamond section sales", "diamond billing"
        ],
        "type": "float",
        "default": 0.0
    },
    "total_revenue": {
        "aliases": [
            "total revenue", "total sales", "overall revenue", "grand total", "net revenue", 
            "total collection", "total turnover", "overall turnover", "overall business revenue", 
            "total business revenue", "overall sales", "total business", "net business revenue",
            "daily sales amount", "total billing", "total daily sales", "gross sales"
        ],
        "type": "float",
        "default": 0.0
    },

    # ── Digital Scheme Metrics ──
    "digigold_enrollments": {
        "aliases": [
            "digigold enrollments", "digigold enrollment", "digigold count", "digi gold count", 
            "digigold nos", "digigold total", "digi gold", "digigold", "dg members", "dg enrollments", 
            "dg count", "digital gold members", "digital gold", "digital membership"
        ],
        "type": "int",
        "default": 0
    },
    "digisilver_enrollments": {
        "aliases": [
            "digisilver enrollments", "digisilver enrollment", "digisilver count", "digi silver count", 
            "digisilver nos", "digisilver total", "digi silver", "digisilver", "ds members", "ds enrollments", 
            "ds count", "digital silver members", "digital silver"
        ],
        "type": "int",
        "default": 0
    },

    # ── HR Metrics ──
    "employees_present": {
        "aliases": [
            "employees present", "employee present", "staff present", "present count", "attendance present", 
            "present staff", "total present", "headcount present", "present", "staff headcount present", 
            "today s attendance", "present headcount", "present staff count", "attendance present count",
            "attendance"
        ],
        "type": "int",
        "default": 0
    },
    "employees_absent": {
        "aliases": [
            "employees absent", "employee absent", "staff absent", "absent count", "attendance absent", 
            "absent staff", "total absent", "headcount absent", "absent", "absent headcount", 
            "absent staff count", "employees on leave", "employee on leave", "staff on leave", "on leave", 
            "leave headcount", "staff leave", "leave count", "employees leave", "employee leave", "leave",
            "absent employees", "absent employee", "leave staff", "leave employees", "total on leave",
            "total leave", "total staff on leave", "no of absent", "no of leave", "number of absent", 
            "number of leave", "no. of absent", "no. of leave", "number of employees on leave"
        ],
        "type": "int",
        "default": 0
    },

    # ── Operational Notes ──
    "customer_complaints": {
        "aliases": ["customer complaints", "complaints", "customer feedback", "complaint summary", "client complaints", "complaint notes"],
        "type": "string",
        "default": "None"
    },
    "operational_issues": {
        "aliases": [
            "operational issues", "operational issue", "issues", "branch issues", 
            "maintenance issues", "ops issues", "operation issues", "store issues", 
            "ops summary", "operational notes", "maintenance & issues", "branch operational issues",
            "operation issue", "ops issue", "branch issue", "store issue", "maintenance issue",
            "issues & maintenance", "issues logged", "operational summary", "operational remarks",
            "daily operational issues", "incident log"
        ],
        "type": "string",
        "default": "None"
    },
    "remarks": {
        "aliases": ["manager remarks", "manager remark", "branch remarks", "remarks", "notes", "comments", "general remarks"],
        "type": "string",
        "default": "None"
    },
    "overall_remarks": {
        "aliases": ["overall remarks", "scheme remarks", "overall remark", "scheme summary remarks"],
        "type": "string",
        "default": "None"
    }
}

# ---------------------------------------------------------------------------
# Employee table column mappings — new production template format
# ---------------------------------------------------------------------------

EMPLOYEE_COLUMN_MAPPINGS = {
    "name": [
        "employee name", "emp name", "staff name", "employee", "staff",
        "sales executive", "name"
    ],
    "gold": [
        "gold", "gold weight", "gold grams", "gold gms", "gold wt",
        "gold g", "gold weight g", "gold grams sold", "gold amount",
        "gold sales", "gold val", "gold value"
    ],
    "diamond": [
        "diamond", "diamond weight", "diamond grams", "diamond cts",
        "diamond wt", "diamond amount", "diamond sales", "diamond value"
    ],
    "platinum": [
        "platinum", "platinum weight", "platinum grams", "platinum wt",
        "plat", "platinum amount", "platinum sales", "platinum value"
    ],
    "silver": [
        "silver", "silver weight", "silver grams", "silver gms",
        "silver wt", "silver g", "silver weight g", "silver grams sold",
        "silver amount", "silver sales", "silver value"
    ],
    "silver_mrp": [
        "silver mrp", "silver mrp value", "silver mrp amount",
        "silver mrp sales", "silver mrp inr", "silver mrp rs"
    ],
    "subhiksham_count": [
        "subhiksham count", "subhiksham nos", "subhiksham no",
        "subhiksham cnt", "subhiksham members", "subhiksham enrollments"
    ],
    "subhiksham_value": [
        "subhiksham value", "subhiksham amt", "subhiksham amount",
        "subhiksham val", "subhiksham revenue", "subhiksham collection"
    ],
    "viruksham_count": [
        "viruksham count", "viruksham nos", "viruksham no",
        "viruksham cnt", "viruksham members", "viruksham enrollments"
    ],
    "viruksham_value": [
        "viruksham value", "viruksham amt", "viruksham amount",
        "viruksham val", "viruksham revenue", "viruksham collection"
    ],
    "digigold": [
        "digigold", "digi gold", "digigold enrollments", "digi gold count",
        "digital gold", "digigold count", "dg", "dg count", "dg enrollments"
    ],
    "digisilver": [
        "digisilver", "digi silver", "digisilver enrollments", "digi silver count",
        "digital silver", "digisilver count", "ds", "ds count", "ds enrollments"
    ],
}
