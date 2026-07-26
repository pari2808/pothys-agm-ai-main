"""
table_parser.py — Direct Column-Mapped Table Parser
====================================================

Production parser for the new Pothys manager Excel template.

The new template uses a FLAT employee table with columns:
  Employee Name | Gold | Diamond | Platinum | Silver | Silver MRP |
  Subhiksham Count | Subhiksham Value | Viruksham Count | Viruksham Value |
  DigiGold | DigiSilver

There are NO section headings, NO separate scheme tables, NO attendance
sections embedded in the data sheet.  The parser simply:

  1. Scans rows for the header row (contains "Employee Name" + at least 2
     other mapped columns).
  2. Maps column indices to field names via EMPLOYEE_COLUMN_MAPPINGS.
  3. Reads all data rows below the header until a blank or "Total" row.
  4. Returns a list of employee dicts with the new field names.
"""

import re
from typing import List, Dict, Any, Optional, Set, Tuple

from app.services.excel_engine.normalizer import (
    SheetMatrix, clean_number, clean_int, clean_string
)
from app.services.excel_engine.field_mappings import (
    EMPLOYEE_COLUMN_MAPPINGS, FIELD_MAPPINGS, match_alias, normalize_text
)

# ---------------------------------------------------------------------------
# Section tokens
# ---------------------------------------------------------------------------

SECTION_UNKNOWN             = "UNKNOWN"
SECTION_EMPLOYEE            = "EMPLOYEE"
SECTION_SCHEME_PERFORMANCE  = "SCHEME_PERFORMANCE"
SECTION_ATTENDANCE          = "ATTENDANCE"
SECTION_TOP_PERFORMERS      = "TOP_PERFORMERS"
SECTION_CUSTOMER_COMPLAINTS = "CUSTOMER_COMPLAINTS"
SECTION_OPERATIONAL_ISSUES  = "OPERATIONAL_ISSUES"
SECTION_MANAGER_REMARKS     = "MANAGER_REMARKS"
SECTION_STORE_OPERATIONS    = "STORE_OPERATIONS"
SECTION_BRANCH_SUMMARY      = "BRANCH_SUMMARY"

# ---------------------------------------------------------------------------
# Heading keyword registry
#
# Order matters: more-specific (longer) phrases must come first so that
# "scheme performance" beats "scheme", and "employee attendance" beats
# "attendance".
# ---------------------------------------------------------------------------

_SECTION_HEADINGS: List[Tuple[str, List[str]]] = [
    (SECTION_SCHEME_PERFORMANCE, [
        "scheme performance",
        "digital scheme performance",
        "scheme enrollment",
        "digital scheme ledger",
        "scheme summary",
        "digi scheme",
        "scheme details",
        "scheme wise performance",
        "scheme wise",
    ]),
    (SECTION_ATTENDANCE, [
        "attendance summary",
        "daily attendance",
        "staff attendance",
        "employee attendance",
        "hr summary",
        "human resources",
        "attendance",
    ]),
    (SECTION_TOP_PERFORMERS, [
        "top performer",
        "top performers",
        "star performer",
        "star performers",
        "best performer",
        "best performers",
    ]),
    (SECTION_CUSTOMER_COMPLAINTS, [
        "customer complaint",
        "customer complaints",
        "complaint summary",
        "customer feedback",
        "client complaints",
    ]),
    (SECTION_OPERATIONAL_ISSUES, [
        "operational issue",
        "operational issues",
        "ops issue",
        "ops issues",
        "operational notes",
        "maintenance issues",
        "operational remarks",
    ]),
    (SECTION_MANAGER_REMARKS, [
        "manager remark",
        "manager remarks",
        "branch remark",
        "branch remarks",
        "overall remark",
        "overall remarks",
    ]),
    (SECTION_STORE_OPERATIONS, [
        "store operation",
        "store operations",
        "branch operation",
        "branch operations",
    ]),
    (SECTION_BRANCH_SUMMARY, [
        "branch summary",
        "daily summary",
        "daily report summary",
    ]),
    # Employee — listed LAST so any more-specific section wins first
    (SECTION_EMPLOYEE, [
        "employee performance",
        "staff performance",
        "employee wise performance",
        "employee wise",
        "staff wise",
        "sales executive performance",
        "employee details",
        "employee table",
        "staff table",
    ]),
]

# Flat normalized keyword sets per section (O(1) membership test)
_SECTION_KEYWORD_SET: Dict[str, Set[str]] = {
    token: {normalize_text(kw) for kw in kws}
    for token, kws in _SECTION_HEADINGS
}

# All heading keywords in one flat set (used to reject header-keyword values
# from appearing as employee / scheme names)
_ALL_HEADING_KEYWORDS: Set[str] = {
    kw for kws in _SECTION_KEYWORD_SET.values() for kw in kws
}

# Terms that must never appear as scheme or employee names
_ATTENDANCE_REJECT_TERMS: Set[str] = {
    normalize_text(t) for t in [
        "employees present", "employees absent", "employee present",
        "employee absent", "staff present", "staff absent",
        "employees on leave", "employee on leave", "staff on leave",
        "on leave", "present", "absent", "leave", "headcount",
        "attendance", "total present", "total absent",
    ]
}

# Scheme name terms that must never appear as employee names
_SCHEME_NAME_TERMS: Set[str] = {
    normalize_text(t) for t in [
        "digigold", "digi gold", "digisilver", "digi silver",
        "premium", "scheme", "digital scheme", "plan",
    ]
}

# Employee column-header terms that must never appear as scheme names
_EMP_HEADER_TERMS: Set[str] = {
    normalize_text(t) for t in [
        "employee", "employee name", "emp name", "staff", "name",
        "designation", "role", "sales executive",
    ]
}


# ---------------------------------------------------------------------------
# Row validation helpers
# ---------------------------------------------------------------------------

_REJECT_NAME_TERMS = {
    normalize_text(t) for t in [
        "total", "grand total", "prepared by", "approved by",
        "employee name", "emp name", "staff name", "name",
        "scheme", "attendance", "summary", "report",
    ]
}


def _is_valid_employee_name(name_val: Optional[str]) -> bool:
    """Return True only if name_val is a genuine employee name."""
    if not name_val or name_val.strip() == "" or name_val == "None":
        return False

    name_norm = normalize_text(name_val)

    # Reject totals, footer rows, and header keywords
    for term in _REJECT_NAME_TERMS:
        if name_norm == term:
            return False
        if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", name_norm):
            return False

    return True


# ---------------------------------------------------------------------------
# Header detection
# ---------------------------------------------------------------------------

def _find_header_row(matrix: SheetMatrix) -> Tuple[Optional[int], Dict[int, str]]:
    """
    Scan rows to find the employee table header.

    Returns (row_index, col_map) where col_map maps column index → field name.
    Returns (None, {}) if no valid header is found.
    """
    for r in range(1, min(matrix.max_row + 1, 50)):
        col_map: Dict[int, str] = {}
        matched_count = 0

        for c in range(1, matrix.max_column + 1):
            val = matrix.get_cell_value(r, c)
            if not val:
                continue
            for col_key, aliases in EMPLOYEE_COLUMN_MAPPINGS.items():
                if col_key in col_map.values():
                    continue
                if match_alias(val, aliases, threshold=0.80) > 0:
                    col_map[c] = col_key
                    matched_count += 1
                    break

        # Valid header: has "name" column + at least 2 other data columns
        if matched_count >= 3 and "name" in col_map.values():
            return r, col_map

    return None, {}


# ---------------------------------------------------------------------------
# SectionSpan — used by extract_scheme_records
# ---------------------------------------------------------------------------

class SectionSpan:
    __slots__ = ("token", "start", "end")

    def __init__(self, token: str, start: int, end: int):
        self.token = token
        self.start = start
        self.end   = end

    def __repr__(self) -> str:
        return f"SectionSpan({self.token!r}, rows={self.start}-{self.end})"


def _row_text_tokens(matrix: SheetMatrix, r: int) -> List[str]:
    tokens = []
    for c in range(1, matrix.max_column + 1):
        v = matrix.get_cell_value(r, c)
        if v is not None:
            t = normalize_text(v)
            if t:
                tokens.append(t)
    return tokens


def _classify_row_as_section(tokens: List[str]) -> Optional[str]:
    for section_token, _ in _SECTION_HEADINGS:
        for phrase_norm in _SECTION_KEYWORD_SET[section_token]:
            for tok in tokens:
                if tok == phrase_norm:
                    return section_token
                if re.search(
                    r"(?<!\w)" + re.escape(phrase_norm) + r"(?!\w)",
                    tok
                ):
                    return section_token
    return None


def _is_employee_table_header(tokens: List[str]) -> bool:
    has_name = any(
        match_alias(tok, EMPLOYEE_COLUMN_MAPPINGS["name"], threshold=0.82) > 0
        for tok in tokens
    )
    has_numeric = any(
        any(
            match_alias(tok, EMPLOYEE_COLUMN_MAPPINGS[key], threshold=0.82) > 0
            for key in [
                "gold", "silver", "platinum",
                "diamond", "digigold", "digisilver",
            ]
        )
        for tok in tokens
    )
    return has_name and has_numeric


def _build_section_spans(matrix: SheetMatrix) -> List[SectionSpan]:
    spans: List[SectionSpan] = []
    current_token: Optional[str] = None
    current_start: Optional[int] = None

    def _flush(close_at: int, new_token: str, new_start: int) -> None:
        nonlocal current_token, current_start
        if current_token is not None and current_start is not None and close_at >= current_start:
            spans.append(SectionSpan(current_token, current_start, close_at))
        current_token = new_token
        current_start = new_start

    for r in range(1, matrix.max_row + 1):
        tokens = _row_text_tokens(matrix, r)
        detected = _classify_row_as_section(tokens)

        if detected is not None:
            _flush(close_at=r - 1, new_token=detected, new_start=r)
            continue

        if current_token is None and _is_employee_table_header(tokens):
            _flush(close_at=r - 1, new_token=SECTION_EMPLOYEE, new_start=r)
            continue

    if current_token is not None and current_start is not None:
        spans.append(SectionSpan(current_token, current_start, matrix.max_row))

    if not spans:
        spans.append(SectionSpan(SECTION_UNKNOWN, 1, matrix.max_row))

    if spans[0].start > 1:
        spans.insert(0, SectionSpan(SECTION_UNKNOWN, 1, spans[0].start - 1))

    if len(spans) == 1 and spans[0].token == SECTION_UNKNOWN:
        title_norm = normalize_text(matrix.title)
        _SCHEME_TITLE_KEYWORDS = {
            "scheme", "scheme performance", "digital scheme",
            "scheme enrollment", "scheme wise", "digi scheme",
        }
        _EMPLOYEE_TITLE_KEYWORDS = {
            "employee", "staff", "kpi", "sales executive",
            "employee performance", "employee wise",
        }
        if any(kw in title_norm for kw in _SCHEME_TITLE_KEYWORDS):
            spans[0] = SectionSpan(SECTION_SCHEME_PERFORMANCE, spans[0].start, spans[0].end)
        elif any(kw in title_norm for kw in _EMPLOYEE_TITLE_KEYWORDS):
            spans[0] = SectionSpan(SECTION_EMPLOYEE, spans[0].start, spans[0].end)

    return spans


def _spans_for_token(spans: List[SectionSpan], token: str) -> List[SectionSpan]:
    return [s for s in spans if s.token == token]


def _build_section_map(matrix: SheetMatrix) -> Dict[int, str]:
    spans = _build_section_spans(matrix)
    section_map: Dict[int, str] = {}
    for span in spans:
        for r in range(span.start, span.end + 1):
            section_map[r] = span.token
    return section_map


# ---------------------------------------------------------------------------
# Main TableParser class
# ---------------------------------------------------------------------------

class TableParser:
    """
    Direct column-mapped table parser for the new production manager template.

    Extracts employee records from a flat table.  No section boundaries,
    no scheme table scanning — the employee table IS the data source.
    """

    @staticmethod
    def extract_employee_records(matrices: List[SheetMatrix]) -> List[Dict[str, Any]]:
        """
        Extract employee performance records from all sheets.

        Scans each sheet for the employee table header row, then reads
        data rows until a blank or "Total" row is encountered.
        """
        all_employees: List[Dict[str, Any]] = []

        for matrix in matrices:
            header_row, col_map = _find_header_row(matrix)
            if header_row is None:
                continue

            # Read data rows below header
            for r in range(header_row + 1, matrix.max_row + 1):
                record = TableParser._extract_row(matrix, r, col_map)

                name_val = record.get("name")

                # Stop at total/summary rows
                if name_val:
                    name_norm = normalize_text(name_val)
                    if any(kw in name_norm for kw in ["total", "grand total"]):
                        break

                # Skip invalid names
                if not _is_valid_employee_name(name_val):
                    # Check if row has any numeric data (unnamed employee)
                    has_data = any(
                        record.get(k, 0) > 0
                        for k in ["gold", "diamond", "platinum", "silver",
                                   "silver_mrp", "digigold", "digisilver",
                                   "subhiksham_count", "subhiksham_value",
                                   "viruksham_count", "viruksham_value"]
                    )
                    if has_data:
                        record["name"] = f"Staff Member #{len(all_employees) + 1}"
                        record["employee_name"] = record["name"]
                    else:
                        # Fully blank row — check if we should stop
                        row_has_any = any(
                            matrix.get_cell_value(r, c) is not None
                            and str(matrix.get_cell_value(r, c)).strip() != ""
                            for c in range(1, matrix.max_column + 1)
                        )
                        if not row_has_any:
                            # Blank row — might be spacing; skip but don't stop
                            continue
                        continue

                all_employees.append(record)

            # Found employees in this sheet — use them
            if all_employees:
                break

        return all_employees

    @staticmethod
    def _extract_row(
        matrix: SheetMatrix, r: int, col_map: Dict[int, str]
    ) -> Dict[str, Any]:
        """Build an employee record dict from the column map for row r."""
        record: Dict[str, Any] = {
            "name": None,
            "gold": 0.0,
            "diamond": 0.0,
            "platinum": 0.0,
            "silver": 0.0,
            "silver_mrp": 0.0,
            "subhiksham_count": 0,
            "subhiksham_value": 0.0,
            "viruksham_count": 0,
            "viruksham_value": 0.0,
            "digigold": 0,
            "digisilver": 0,
        }

        for c, col_key in col_map.items():
            cell_val = matrix.get_cell_value(r, c)
            if col_key == "name":
                val_str = clean_string(cell_val, default="")
                if val_str:
                    record["name"] = val_str
            elif col_key in ("digigold", "digisilver", "subhiksham_count", "viruksham_count"):
                record[col_key] = clean_int(cell_val)
            else:
                record[col_key] = clean_number(cell_val)

        # Normalised aliases expected by downstream consumers
        record["employee_name"] = record["name"] or "Staff Member"

        # Compute total sales for sorting/ranking
        record["sales"] = float(
            record["gold"] + record["silver"]
            + record["platinum"] + record["diamond"]
        )

        return record

    # -----------------------------------------------------------------------
    # Scheme extraction
    # -----------------------------------------------------------------------

    _SCHEME_COLUMN_ALIASES: Dict[str, List[str]] = {
        "scheme_name": [
            "scheme", "scheme name", "plan", "digital scheme", "scheme type",
            "schemes", "digital schemes", "particulars", "scheme description",
            "scheme / plan",
        ],
        "enrollments": [
            "today's enrollments", "today s enrollments", "enrollments",
            "enrollment", "members", "count", "enrollment count",
            "today enrollments", "no of enrollments", "no. of enrollments",
            "total enrollments", "new enrollments", "enrollments count",
        ],
        "revenue": [
            "revenue", "revenue inr", "amount", "total revenue", "revenue rs",
            "collection", "sales", "revenue (inr)", "amount (inr)",
            "amount (rs)", "total amount", "revenue (₹)", "amount (₹)",
            "collection (rs)",
        ],
        "remarks": [
            "remarks", "notes", "comments", "remark", "manager remarks",
        ],
    }

    @staticmethod
    def extract_scheme_records(matrices: List[SheetMatrix]) -> List[Dict[str, Any]]:
        """
        Locate and extract scheme performance table rows.

        Algorithm:
          1. Build section spans for each sheet.
          2. Collect all SCHEME_PERFORMANCE spans.
          3. Within each span's [start, end] window ONLY, find the first
             valid column header row.
          4. Read data rows from header_row+1 to span.end — NEVER beyond.
          5. Validate each row: scheme_name must be a real scheme name.
             Attendance rows are structurally excluded because they live in
             a different span with separate [start, end] boundaries.
        """
        scheme_records: List[Dict[str, Any]] = []

        for matrix in matrices:
            spans = _build_section_spans(matrix)
            scheme_spans = _spans_for_token(spans, SECTION_SCHEME_PERFORMANCE)
            if not scheme_spans:
                continue

            for span in scheme_spans:
                # Find the header row ONLY within this span's window
                header_row, col_map = TableParser._find_scheme_header_row_in_span(
                    matrix, span
                )
                if header_row is None:
                    continue

                # Read data rows strictly within [header_row+1, span.end]
                for r in range(header_row + 1, span.end + 1):
                    row_record = TableParser._extract_scheme_row(matrix, r, col_map)
                    if row_record is None:
                        # Sparse row — scheme tables can have internal spacing
                        continue

                    s_name = row_record.get("scheme_name")
                    if not TableParser._is_valid_scheme_name(s_name):
                        # If name signals a new section, stop reading this span early
                        if s_name and TableParser._is_section_stop_name(s_name):
                            break
                        continue

                    scheme_records.append(row_record)

            if scheme_records:
                break  # Found records in this matrix — skip remaining matrices

        return scheme_records

    @staticmethod
    def _find_scheme_header_row_in_span(
        matrix: SheetMatrix,
        span: SectionSpan,
    ) -> Tuple[Optional[int], Dict[int, str]]:
        """
        Among rows in [span.start, span.end], return the first row that
        contains a valid scheme table column header.
        Returns (row_index, col_map) or (None, {}) if not found.
        """
        for r in range(span.start, span.end + 1):
            col_map: Dict[int, str] = {}
            matched_count = 0

            for c in range(1, matrix.max_column + 1):
                val = matrix.get_cell_value(r, c)
                if not val:
                    continue
                for col_key, aliases in TableParser._SCHEME_COLUMN_ALIASES.items():
                    if col_key in col_map.values():
                        continue
                    if match_alias(val, aliases, threshold=0.80) > 0:
                        col_map[c] = col_key
                        matched_count += 1
                        break

            has_scheme_col = "scheme_name" in col_map.values()
            has_metric_col = (
                "enrollments" in col_map.values()
                or "revenue" in col_map.values()
            )

            if matched_count >= 2 and has_scheme_col and has_metric_col:
                return r, col_map

        return None, {}

    @staticmethod
    def _extract_scheme_row(
        matrix: SheetMatrix, r: int, col_map: Dict[int, str]
    ) -> Optional[Dict[str, Any]]:
        """
        Build a scheme record from the column map.  Returns None if the row
        has no data at all in the mapped columns.
        """
        s_name: Optional[str] = None
        enrollments: int = 0
        revenue: float = 0.0
        row_has_data = False

        for c, col_key in col_map.items():
            c_val = matrix.get_cell_value(r, c)
            if c_val is not None and str(c_val).strip() != "":
                row_has_data = True
                if col_key == "scheme_name":
                    s_name = clean_string(c_val)
                elif col_key == "enrollments":
                    enrollments = clean_int(c_val)
                elif col_key == "revenue":
                    revenue = clean_number(c_val)

        if not row_has_data:
            return None

        return {
            "scheme_name": s_name,
            "enrollments": int(enrollments),
            "revenue": float(revenue),
        }

    @staticmethod
    def _is_valid_scheme_name(s_name: Optional[str]) -> bool:
        """
        Return True only if s_name is a genuine scheme name.

        Rejects: None, "None", attendance terms, employee column header
        names, section heading keywords, and total rows.
        """
        if not s_name or s_name == "None":
            return False

        name_norm = normalize_text(s_name)

        # Reject totals / footer rows
        if any(kw in name_norm for kw in ["total", "grand total", "prepared by", "approved by"]):
            return False

        # Reject attendance terms — these must NEVER appear as scheme names
        if name_norm in _ATTENDANCE_REJECT_TERMS:
            return False
        for term in _ATTENDANCE_REJECT_TERMS:
            if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", name_norm):
                return False

        # Reject employee column header values being mis-read as scheme names
        if name_norm in _EMP_HEADER_TERMS:
            return False

        # Reject section heading keywords
        for kw in _ALL_HEADING_KEYWORDS:
            if re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", name_norm):
                return False

        return True

    @staticmethod
    def _is_section_stop_name(s_name: str) -> bool:
        """
        Return True if the scheme_name cell contains text that signals we
        have overrun into another section.  This is a belt-and-suspenders
        guard — the span boundary should normally prevent this entirely.
        """
        name_norm = normalize_text(s_name)
        stop_phrases = {
            "top performer", "customer complaint", "operational issue",
            "manager remark", "overall remark", "store operation",
            "branch summary", "attendance",
        }
        return any(
            re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", name_norm)
            for phrase in stop_phrases
        )
