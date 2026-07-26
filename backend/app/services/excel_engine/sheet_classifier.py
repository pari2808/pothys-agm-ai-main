from typing import Dict, List
from app.services.excel_engine.normalizer import SheetMatrix
from app.services.excel_engine.field_mappings import normalize_text, EMPLOYEE_COLUMN_MAPPINGS, match_alias


class SheetClassifier:
    """Classifies sheets based on cell contents — simplified for new template."""

    @staticmethod
    def classify_workbook(matrices: List[SheetMatrix]) -> Dict[str, List[SheetMatrix]]:
        """
        Classify sheets into categories.

        For the new template, the primary distinction is:
        - 'data': sheets containing the employee data table
        - 'metadata': sheets with only metadata/summary labels

        All sheets are returned for scanning; the parser will find
        the header row wherever it exists.
        """
        classified = {
            "data": [],
            "metadata": [],
            "all": list(matrices),
        }

        for matrix in matrices:
            has_employee_table = False

            # Scan first 50 rows for employee table headers
            for r in range(1, min(matrix.max_row + 1, 50)):
                col_matches = 0
                has_name = False
                for c in range(1, min(matrix.max_column + 1, 20)):
                    val = matrix.get_cell_value(r, c)
                    if not val:
                        continue
                    for col_key, aliases in EMPLOYEE_COLUMN_MAPPINGS.items():
                        if match_alias(val, aliases, threshold=0.80) > 0:
                            col_matches += 1
                            if col_key == "name":
                                has_name = True
                            break

                if has_name and col_matches >= 3:
                    has_employee_table = True
                    break

            # Title-based fallback
            if not has_employee_table:
                title_norm = normalize_text(matrix.title)
                if any(kw in title_norm for kw in ["employee", "staff", "kpi", "performance"]):
                    has_employee_table = True

            if has_employee_table:
                classified["data"].append(matrix)
            else:
                classified["metadata"].append(matrix)

        return classified
