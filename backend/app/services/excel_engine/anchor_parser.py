"""
anchor_parser.py — Metadata Extractor
======================================

Scans Excel sheets for scalar key-value metadata fields:
  - Report Date
  - Branch Name
  - Manager Name
  - Sub Manager Name
  - Employees Present / Absent
  - Customer Complaints
  - Operational Issues
  - Manager Remarks

These are label → value pairs found in header/metadata rows,
NOT part of the employee data table.
"""

import re
from typing import Dict, Any, List, Optional
from app.services.excel_engine.normalizer import SheetMatrix, clean_number, clean_int, clean_string, clean_date
from app.services.excel_engine.field_mappings import FIELD_MAPPINGS, match_alias, EMPLOYEE_COLUMN_MAPPINGS


class AnchorParser:
    """Scans sheets to locate scalar key-value fields dynamically via label anchors."""

    @staticmethod
    def extract_summary(matrices: List[SheetMatrix]) -> Dict[str, Any]:
        results = {}
        best_scores = {}

        # Initialize defaults
        for field_name, meta in FIELD_MAPPINGS.items():
            results[field_name] = meta.get("default")
            best_scores[field_name] = 0.0

        for matrix in matrices:
            max_r = min(matrix.max_row + 1, 100)
            max_c = min(matrix.max_column + 1, 30)

            # Identify table header & data rows to skip them during metadata scanning
            table_rows = set()
            for r in range(1, max_r):
                has_name_col = False
                col_matches = 0
                seen_vals = set()
                for c in range(1, max_c):
                    v = matrix.get_cell_value(r, c)
                    if v and v not in seen_vals:
                        seen_vals.add(v)
                        if match_alias(v, EMPLOYEE_COLUMN_MAPPINGS["name"], threshold=0.82) > 0:
                            has_name_col = True
                        if any(match_alias(v, aliases, threshold=0.82) > 0 for aliases in EMPLOYEE_COLUMN_MAPPINGS.values()):
                            col_matches += 1
                if has_name_col and col_matches >= 3:
                    # Mark header row and data rows beneath it as table rows
                    table_rows.add(r)
                    empty_count = 0
                    for dr in range(r + 1, max_r):
                        row_cells = [matrix.get_cell_value(dr, c) for c in range(1, max_c)]
                        if any(v is not None and str(v).strip() != "" for v in row_cells):
                            table_rows.add(dr)
                            empty_count = 0
                        else:
                            empty_count += 1
                            if empty_count >= 3:
                                break

            for r in range(1, max_r):
                if r in table_rows:
                    continue

                for c in range(1, max_c):
                    cell_val = matrix.get_cell_value(r, c)
                    if not cell_val:
                        continue

                    # Try matching each field in FIELD_MAPPINGS
                    for field_name, meta in FIELD_MAPPINGS.items():
                        score = match_alias(cell_val, meta["aliases"], threshold=0.82)
                        prev_score = best_scores.get(field_name, 0.0)
                        prev_val = results.get(field_name)
                        if score > 0 and (score > prev_score or (score == prev_score and (prev_val is None or prev_val == 0 or prev_val == "None"))):
                            val = AnchorParser._extract_adjacent_value(matrix, r, c, meta["type"])
                            if val is not None:
                                if score > prev_score or (prev_val is None or prev_val == 0 or prev_val == "None") or (val != 0 and val != "None"):
                                    results[field_name] = val
                                    best_scores[field_name] = score

        return results

    @staticmethod
    def _parse_typed_value(raw_val: Any, target_type: str, label_val: Any = None) -> Any:
        """Utility to parse and clean raw scalar values based on target type."""
        if raw_val is None:
            return None

        s_raw = str(raw_val).strip()
        if not s_raw or (label_val and s_raw == str(label_val).strip()):
            return None

        if target_type == "float":
            s_clean = re.sub(r"(?i)\b(inr|rs|rupees)\b\.?", "", s_raw)
            s_clean = re.sub(r"[₹$,/\-:=+]", "", s_clean).replace(",", "").strip()
            try:
                res = float(s_clean)
                if res != 0.0 or s_clean in ["0", "0.0", "0.00"]:
                    return res
            except ValueError:
                match = re.search(r"[-+]?\d*\.?\d+", s_clean)
                if match:
                    try:
                        return float(match.group(0))
                    except ValueError:
                        pass
        elif target_type == "int":
            s_lower = s_raw.lower()
            if s_lower in ["nil", "none", "n/a", "na", "-", "0", "0.0", "zero", ""]:
                return 0
            
            s_clean = re.sub(r"(?i)\b(inr|rs|rupees|nos|count|members|enrollments|headcount|staff|employees|present|absent|leave|on leave)\b\.?", "", s_raw)
            s_clean = re.sub(r"[₹$,/\-:=+]", "", s_clean).replace(",", "").strip()
            try:
                f_val = float(s_clean)
                return int(round(f_val))
            except ValueError:
                match = re.search(r"\d+", s_raw)
                if match:
                    return int(match.group(0))
        elif target_type == "date":
            dt_res = clean_date(raw_val)
            if dt_res:
                return dt_res
        elif target_type == "string":
            s_res = clean_string(raw_val)
            if s_res != "None":
                return s_res
        return None

    @staticmethod
    def _extract_adjacent_value(matrix: SheetMatrix, r: int, c: int, target_type: str) -> Any:
        """Looks to inline text, immediate right, right + radius, or below for value cell."""
        label_val = matrix.get_cell_value(r, c)
        
        # 1. Check inline label value first (e.g. "Employees on Leave = 2" or "Employees on Leave: 2")
        if label_val:
            label_str = str(label_val).strip()
            for delim in [":", "-", "="]:
                if delim in label_str:
                    parts = label_str.split(delim, 1)
                    if len(parts) == 2 and parts[1].strip():
                        val = AnchorParser._parse_typed_value(parts[1].strip(), target_type)
                        if val is not None:
                            return val

            # Inline regex fallback for space/parentheses trailing digits
            inline_match = re.search(r"^(.*?)(?:[:\-=\s(]+)(\d+)\s*(?:nos|count|staff|members|employees|persons|\))?$", label_str, re.IGNORECASE)
            if inline_match:
                val = AnchorParser._parse_typed_value(inline_match.group(2), target_type)
                if val is not None:
                    return val

        end_c = c
        for rng in matrix.worksheet.merged_cells.ranges:
            if rng.min_row <= r <= rng.max_row and rng.min_col <= c <= rng.max_col:
                end_c = rng.max_col
                break

        # Same-row candidates first (most common for label-value metadata pairs)
        candidates = [
            (r, end_c + 1),
            (r, end_c + 2),
            (r, end_c + 3),
            (r, end_c + 4),
        ]

        for cand_r, cand_c in candidates:
            if cand_r <= matrix.max_row and cand_c <= matrix.max_column:
                raw_val = matrix.get_cell_value(cand_r, cand_c)
                if not raw_val:
                    continue

                # Stop if candidate cell is another metadata label anchor
                cand_str = str(raw_val).strip()
                is_label = False
                for meta in FIELD_MAPPINGS.values():
                    if match_alias(cand_str, meta["aliases"], threshold=0.82) > 0:
                        is_label = True
                        break
                if is_label:
                    # Don't absorb adjacent labels as values
                    continue

                parsed_val = AnchorParser._parse_typed_value(raw_val, target_type, label_val=label_val)
                if parsed_val is not None:
                    return parsed_val

        return None
