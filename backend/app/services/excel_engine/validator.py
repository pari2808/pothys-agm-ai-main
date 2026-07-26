from typing import Dict, Any, List


class ExtractionValidator:
    """Validates extracted data and builds diagnostic reports for the new production template."""

    @staticmethod
    def validate_and_build_diagnostics(
        summary_data: Dict[str, Any],
        employees_data: List[Dict[str, Any]],
        scheme_data: Dict[str, Any],
        branch_totals: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        warnings = []
        missing_fields = []
        extracted_count = 0

        bt = branch_totals or {}

        # Check branch-level aggregated fields
        aggregated_fields = [
            ("gold", bt.get("gold", 0)),
            ("diamond", bt.get("diamond", 0)),
            ("platinum", bt.get("platinum", 0)),
            ("silver", bt.get("silver", 0)),
            ("silver_mrp", bt.get("silver_mrp", 0)),
            ("digigold", bt.get("digigold", 0)),
            ("digisilver", bt.get("digisilver", 0)),
        ]

        for field, val in aggregated_fields:
            if val is not None and val != 0 and val != 0.0:
                extracted_count += 1
            else:
                missing_fields.append(field)
                warnings.append(f"Aggregated field '{field}' is zero or missing.")

        # Check metadata fields
        metadata_fields = [
            "employees_present", "employees_absent",
            "customer_complaints", "operational_issues", "remarks"
        ]
        for field in metadata_fields:
            val = summary_data.get(field)
            if val is not None and val != "None" and val != 0 and val != 0.0:
                extracted_count += 1
            else:
                missing_fields.append(field)
                warnings.append(f"Metadata field '{field}' was not found or has default value ({val}).")

        # Employee check
        emp_count = len(employees_data)
        if emp_count > 0:
            extracted_count += 5
        else:
            warnings.append("No employee performance records extracted.")

        # Scheme summary check
        sub_count = scheme_data.get("subhiksham_count", 0)
        sub_value = scheme_data.get("subhiksham_value", 0)
        vir_count = scheme_data.get("viruksham_count", 0)
        vir_value = scheme_data.get("viruksham_value", 0)

        if sub_count == 0 and sub_value == 0:
            warnings.append("Subhiksham count and value are both zero.")
        if vir_count == 0 and vir_value == 0:
            warnings.append("Viruksham count and value are both zero.")

        # Calculate confidence score
        total_possible = len(aggregated_fields) + len(metadata_fields) + 5
        confidence_score = min(1.0, round(extracted_count / max(total_possible, 1), 2))
        if confidence_score < 0.3:
            status = "CRITICAL_MISSING"
        elif missing_fields:
            status = "PARTIAL_SUCCESS"
        else:
            status = "SUCCESS"

        # Build formatted report
        def fmt_val(val: Any) -> str:
            try:
                f = float(val or 0.0)
                return f"{f:,.2f}" if f > 0 else "0"
            except Exception:
                return str(val)

        report_lines = [
            f"{'✓' if bt.get('gold') else '✘'} Gold → {fmt_val(bt.get('gold'))}",
            f"{'✓' if bt.get('diamond') else '✘'} Diamond → {fmt_val(bt.get('diamond'))}",
            f"{'✓' if bt.get('platinum') else '✘'} Platinum → {fmt_val(bt.get('platinum'))}",
            f"{'✓' if bt.get('silver') else '✘'} Silver → {fmt_val(bt.get('silver'))}",
            f"{'✓' if bt.get('silver_mrp') else '✘'} Silver MRP → {fmt_val(bt.get('silver_mrp'))}",
            f"{'✓' if bt.get('digigold') else '✘'} DigiGold → {bt.get('digigold', 0)}",
            f"{'✓' if bt.get('digisilver') else '✘'} DigiSilver → {bt.get('digisilver', 0)}",
            f"{'✓' if summary_data.get('employees_present') else '✘'} Present → {summary_data.get('employees_present', 0)}",
            f"{'✓' if summary_data.get('employees_absent') else '✘'} Absent → {summary_data.get('employees_absent', 0)}",
            f"Employees extracted: {emp_count}",
            f"Subhiksham: count={sub_count}, value={fmt_val(sub_value)}",
            f"Viruksham: count={vir_count}, value={fmt_val(vir_value)}",
            "",
            f"Confidence Score: {int(confidence_score * 100)}%",
            "",
            "Warnings:"
        ]
        if warnings:
            for w in warnings:
                report_lines.append(f"- {w}")
        else:
            report_lines.append("None")

        report_text = "\n".join(report_lines)

        return {
            "status": status,
            "confidence_score": confidence_score,
            "extracted_fields_count": extracted_count,
            "missing_fields": missing_fields,
            "warnings": warnings,
            "report_text": report_text,
        }
