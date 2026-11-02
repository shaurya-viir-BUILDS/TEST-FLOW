#!/usr/bin/env python3
"""Generate a standalone, neutral, fully synthetic TestFlow demo dataset."""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).parent / "seed_data.json"
SYNTHETIC = "SYNTHETIC_DEMO"


def d(s: str) -> str:
    return s


def main() -> None:
    employees = [
        {"employee_id": "EMP-SYN-001", "display_name": "Synthetic Manager One", "role": "management", "active": True},
        {"employee_id": "EMP-SYN-002", "display_name": "Synthetic Manager Two", "role": "management", "active": True},
        {"employee_id": "EMP-SYN-003", "display_name": "Synthetic HR One", "role": "hr", "active": True},
        {"employee_id": "EMP-SYN-004", "display_name": "Synthetic HR Two", "role": "hr", "active": True},
        {"employee_id": "EMP-SYN-005", "display_name": "Synthetic Test Lead One", "role": "test_lead", "active": True},
        {"employee_id": "EMP-SYN-006", "display_name": "Synthetic Test Lead Two", "role": "test_lead", "active": True},
    ] + [
        {"employee_id": f"EMP-SYN-{i:03d}", "display_name": f"Synthetic Tester {i-6}", "role": "tester", "active": True}
        for i in range(7, 13)
    ]

    clients = [
        {"client_id": "CLI-SYN-001", "name": "Northstar Signal Works", "label": SYNTHETIC},
        {"client_id": "CLI-SYN-002", "name": "Blue Orbit Devices", "label": SYNTHETIC},
        {"client_id": "CLI-SYN-003", "name": "Cedar Loop Electronics", "label": SYNTHETIC},
    ]

    product_models = [
        {"model_id": "MOD-SYN-001", "model_code": "WF-RTR-100", "category": "wifi_router", "name": "Synthetic Wave Router 100", "client_id": "CLI-SYN-001", "test_template_id": "TPL-SYN-001"},
        {"model_id": "MOD-SYN-002", "model_code": "WF-RTR-220", "category": "wifi_router", "name": "Synthetic Wave Router 220", "client_id": "CLI-SYN-001", "test_template_id": "TPL-SYN-001"},
        {"model_id": "MOD-SYN-003", "model_code": "RM-KEY-010", "category": "remote", "name": "Synthetic Key Remote 010", "client_id": "CLI-SYN-002", "test_template_id": "TPL-SYN-002"},
        {"model_id": "MOD-SYN-004", "model_code": "RM-KEY-020", "category": "remote", "name": "Synthetic Key Remote 020", "client_id": "CLI-SYN-002", "test_template_id": "TPL-SYN-002"},
        {"model_id": "MOD-SYN-005", "model_code": "STB-VIEW-300", "category": "set_top_box", "name": "Synthetic View Box 300", "client_id": "CLI-SYN-003", "test_template_id": "TPL-SYN-003"},
        {"model_id": "MOD-SYN-006", "model_code": "STB-VIEW-500", "category": "set_top_box", "name": "Synthetic View Box 500", "client_id": "CLI-SYN-003", "test_template_id": "TPL-SYN-004"},
    ]

    templates = [
        {"template_id": "TPL-SYN-001", "name": "Synthetic Wi-Fi Router Functional QA", "version": 1, "steps": [
            {"step_id": "STP-SYN-001-01", "sequence": 1, "name": "Power-on current", "measurement_unit": "A", "valid_range": {"min": 0.20, "max": 0.80}},
            {"step_id": "STP-SYN-001-02", "sequence": 2, "name": "2.4 GHz throughput", "measurement_unit": "Mbps", "valid_range": {"min": 35, "max": 120}},
            {"step_id": "STP-SYN-001-03", "sequence": 3, "name": "5 GHz throughput", "measurement_unit": "Mbps", "valid_range": {"min": 120, "max": 600}},
        ]},
        {"template_id": "TPL-SYN-002", "name": "Synthetic Remote Control Input QA", "version": 1, "steps": [
            {"step_id": "STP-SYN-002-01", "sequence": 1, "name": "Key response latency", "measurement_unit": "ms", "valid_range": {"min": 1, "max": 150}},
            {"step_id": "STP-SYN-002-02", "sequence": 2, "name": "IR output strength", "measurement_unit": "mW/sr", "valid_range": {"min": 2.0, "max": 8.0}},
            {"step_id": "STP-SYN-002-03", "sequence": 3, "name": "Battery idle draw", "measurement_unit": "uA", "valid_range": {"min": 0, "max": 80}},
        ]},
        {"template_id": "TPL-SYN-003", "name": "Synthetic Set-top Box Basic QA", "version": 1, "steps": [
            {"step_id": "STP-SYN-003-01", "sequence": 1, "name": "Boot time", "measurement_unit": "s", "valid_range": {"min": 5, "max": 45}},
            {"step_id": "STP-SYN-003-02", "sequence": 2, "name": "HDMI signal lock", "measurement_unit": "s", "valid_range": {"min": 1, "max": 10}},
            {"step_id": "STP-SYN-003-03", "sequence": 3, "name": "Ethernet link rate", "measurement_unit": "Mbps", "valid_range": {"min": 90, "max": 1000}},
        ]},
        {"template_id": "TPL-SYN-004", "name": "Synthetic Set-top Box Extended QA", "version": 1, "steps": [
            {"step_id": "STP-SYN-004-01", "sequence": 1, "name": "Boot time", "measurement_unit": "s", "valid_range": {"min": 5, "max": 45}},
            {"step_id": "STP-SYN-004-02", "sequence": 2, "name": "HDMI signal lock", "measurement_unit": "s", "valid_range": {"min": 1, "max": 10}},
            {"step_id": "STP-SYN-004-03", "sequence": 3, "name": "Thermal steady state", "measurement_unit": "C", "valid_range": {"min": 25, "max": 70}},
            {"step_id": "STP-SYN-004-04", "sequence": 4, "name": "Standby power", "measurement_unit": "W", "valid_range": {"min": 0.2, "max": 3.0}},
        ]},
    ]

    batch_specs = [
        ("BAT-SYN-001", "MOD-SYN-001", "2026-08-03", 0, "awaiting_registration"),
        ("BAT-SYN-002", "MOD-SYN-002", "2026-08-10", 18, "in_testing"),
        ("BAT-SYN-003", "MOD-SYN-003", "2026-08-24", 16, "completed"),
        ("BAT-SYN-004", "MOD-SYN-004", "2026-09-07", 14, "quality_review"),
        ("BAT-SYN-005", "MOD-SYN-005", "2026-09-21", 20, "completed"),
        ("BAT-SYN-006", "MOD-SYN-006", "2026-10-05", 17, "partially_tested"),
        ("BAT-SYN-007", "MOD-SYN-001", "2026-10-19", 15, "rejected"),
        ("BAT-SYN-008", "MOD-SYN-002", "2026-10-26", 20, "completed"),
    ]
    batches = [{"batch_id": bid, "batch_code": f"SYN-{bid[-3:]}", "model_id": mid, "received_date": rd, "quantity": qty, "lifecycle_status": status, "synthetic": True} for bid, mid, rd, qty, status in batch_specs]

    # Product distributions intentionally include pending, retest, rejected, and passed cases.
    product_status_by_batch = {
        "BAT-SYN-002": ["pending"] * 6 + ["passed"] * 10 + ["failed_awaiting_retest"] * 2,
        "BAT-SYN-003": ["passed"] * 16,
        "BAT-SYN-004": ["passed"] * 12 + ["quality_review"] * 2,
        "BAT-SYN-005": ["passed"] * 18 + ["rejected"] * 2,
        "BAT-SYN-006": ["pending"] * 7 + ["passed"] * 10,
        "BAT-SYN-007": ["rejected"] * 3 + ["passed"] * 12,
        "BAT-SYN-008": ["passed"] * 20,
    }
    products = []
    product_counter = 1
    for bid, mid, _, qty, _ in batch_specs:
        for idx in range(qty):
            serial = f"SYN-TF-{product_counter:04d}"
            status = product_status_by_batch[bid][idx]
            products.append({"product_id": f"PRD-SYN-{product_counter:04d}", "serial_number": serial, "batch_id": bid, "model_id": mid, "status": status, "synthetic": True})
            product_counter += 1

    model_by_id = {m["model_id"]: m for m in product_models}
    template_by_id = {t["template_id"]: t for t in templates}
    tester_ids = [e["employee_id"] for e in employees if e["role"] == "tester"]
    assignments, results = [], []
    defects = []
    assignment_counter = 1
    result_counter = 1
    defect_counter = 1
    # Deterministic measurement helpers keyed by step type.
    def in_range(step):
        lo, hi = step["valid_range"]["min"], step["valid_range"]["max"]
        return round((lo + hi) / 2, 2)
    def out_range(step):
        lo, hi = step["valid_range"]["min"], step["valid_range"]["max"]
        return round(hi + max(1, (hi - lo) * 0.1), 2)

    for p in products:
        template_id = model_by_id[p["model_id"]]["test_template_id"]
        template = template_by_id[template_id]
        aid = f"ASN-SYN-{assignment_counter:04d}"
        assignment_counter += 1
        assignment_status = "pending" if p["status"] == "pending" else "completed"
        if p["status"] == "failed_awaiting_retest":
            assignment_status = "retest_required"
        assignments.append({"assignment_id": aid, "product_id": p["product_id"], "template_id": template_id, "assigned_to_employee_id": tester_ids[(assignment_counter - 2) % len(tester_ids)], "assigned_date": "2026-10-28", "status": assignment_status})
        for step_index, step in enumerate(template["steps"]):
            result_status = "pass"
            measurement = in_range(step)
            notes = "Synthetic measurement within configured range."
            if p["status"] == "pending" and step_index >= 1:
                result_status, measurement, notes = "pending", None, "Synthetic pending step; batch is only partially tested."
            elif p["status"] in {"failed_awaiting_retest", "rejected"} and step_index == 0:
                result_status, measurement, notes = "fail", out_range(step), "Synthetic out-of-range measurement; defect or retest path required."
                defects.append({"defect_id": f"DEF-SYN-{defect_counter:03d}", "product_id": p["product_id"], "batch_id": p["batch_id"], "test_result_id": f"RES-SYN-{result_counter:04d}", "severity": "major" if p["status"] == "failed_awaiting_retest" else "critical", "category": "functional_measurement", "description": "Synthetic failure created for demonstration of containment and corrective action.", "status": "awaiting_retest" if p["status"] == "failed_awaiting_retest" else "closed_rejected", "resolution": "Queued for synthetic retest" if p["status"] == "failed_awaiting_retest" else "Rejected after synthetic review"})
                defect_counter += 1
            elif p["status"] == "rejected":
                notes = "Synthetic rejected item; no unresolved failure on a passing product."
            results.append({"result_id": f"RES-SYN-{result_counter:04d}", "assignment_id": aid, "product_id": p["product_id"], "step_id": step["step_id"], "status": result_status, "measurement_value": measurement, "measurement_unit": step["measurement_unit"], "tested_at": "2026-10-29", "notes": notes})
            result_counter += 1

    # Add resolved historical defects on passed products to make defect reporting realistic.
    for i, p in enumerate([p for p in products if p["status"] == "passed"][:8], start=1):
        defects.append({"defect_id": f"DEF-SYN-{defect_counter:03d}", "product_id": p["product_id"], "batch_id": p["batch_id"], "test_result_id": None, "severity": "minor", "category": "cosmetic", "description": "Synthetic cosmetic observation recorded and corrected before approval.", "status": "resolved", "resolution": "Synthetic rework completed and verified"})
        defect_counter += 1

    quality_reviews = []
    for i, (bid, status) in enumerate([("BAT-SYN-003", "approved"), ("BAT-SYN-004", "pending"), ("BAT-SYN-005", "approved"), ("BAT-SYN-007", "rejected"), ("BAT-SYN-008", "approved"), ("BAT-SYN-002", "pending"), ("BAT-SYN-006", "pending"), ("BAT-SYN-005", "approved")], start=1):
        quality_reviews.append({"quality_review_id": f"QAR-SYN-{i:03d}", "batch_id": bid, "reviewed_by_employee_id": "EMP-SYN-005", "review_date": f"2026-10-{10+i:02d}", "status": status, "notes": "Synthetic quality review record for dashboard and workflow demonstration."})

    attendance = []
    workdays = []
    cur = date(2026, 8, 1)
    end = date(2026, 10, 31)
    while cur <= end:
        if cur.weekday() < 5:
            workdays.append(cur)
        cur += timedelta(days=1)
    for day_index, day in enumerate(workdays):
        for emp_index, emp in enumerate(employees):
            status = "present"
            if (day_index + emp_index) % 53 == 0:
                status = "absent"
            elif (day_index * 2 + emp_index) % 47 == 0:
                status = "leave"
            elif (day_index + emp_index) % 31 == 0:
                status = "half_day"
            elif (day_index * 3 + emp_index) % 19 == 0:
                status = "late"
            attendance.append({"attendance_id": f"ATT-SYN-{len(attendance)+1:04d}", "employee_id": emp["employee_id"], "attendance_date": day.isoformat(), "status": status, "synthetic": True})

    attendance_import_rows = [
        {"row_id": "IMP-SYN-001", "source_label": "synthetic_invalid_attendance.csv", "employee_id": "EMP-SYN-999", "attendance_date": "2026-09-14", "status": "present", "valid": False, "error": "Unknown employee_id"},
        {"row_id": "IMP-SYN-002", "source_label": "synthetic_invalid_attendance.csv", "employee_id": "EMP-SYN-003", "attendance_date": "2026-09-31", "status": "present", "valid": False, "error": "Invalid calendar date"},
        {"row_id": "IMP-SYN-003", "source_label": "synthetic_invalid_attendance.csv", "employee_id": "EMP-SYN-004", "attendance_date": "2026-09-15", "status": "vacationish", "valid": False, "error": "Unsupported attendance status"},
        {"row_id": "IMP-SYN-004", "source_label": "synthetic_invalid_attendance.csv", "employee_id": "", "attendance_date": "2026-09-16", "status": "present", "valid": False, "error": "Missing employee_id"},
    ]

    dispatches = [
        {"dispatch_id": "DSP-SYN-001", "dispatch_date": "2026-09-01", "batch_id": "BAT-SYN-003", "status": "dispatched", "product_ids": [p["product_id"] for p in products if p["batch_id"] == "BAT-SYN-003"], "quality_approval": "approved"},
        {"dispatch_id": "DSP-SYN-002", "dispatch_date": "2026-09-28", "batch_id": "BAT-SYN-005", "status": "dispatched", "product_ids": [p["product_id"] for p in products if p["batch_id"] == "BAT-SYN-005" and p["status"] == "passed"], "quality_approval": "approved"},
        {"dispatch_id": "DSP-SYN-003", "dispatch_date": "2026-10-30", "batch_id": "BAT-SYN-008", "status": "ready", "product_ids": [p["product_id"] for p in products if p["batch_id"] == "BAT-SYN-008"], "quality_approval": "approved"},
        {"dispatch_id": "DSP-SYN-004", "dispatch_date": "2026-10-31", "batch_id": "BAT-SYN-004", "status": "held", "product_ids": [], "quality_approval": "pending"},
        {"dispatch_id": "DSP-SYN-005", "dispatch_date": "2026-10-31", "batch_id": "BAT-SYN-007", "status": "blocked", "product_ids": [], "quality_approval": "rejected"},
    ]

    data = {
        "dataset_metadata": {"dataset_id": "TESTFLOW-SYNTHETIC-DEMO-001", "label": SYNTHETIC, "generated_on": "2026-11-01", "schema_version": "neutral-v1", "description": "Standalone synthetic TestFlow demo data; contains no real people, companies, addresses, customer records, contacts, passwords, or secrets."},
        "employees": employees, "clients": clients, "product_models": product_models, "test_templates": templates, "batches": batches, "products": products,
        "test_assignments": assignments, "test_results": results, "defects": defects, "quality_reviews": quality_reviews, "attendance_records": attendance, "attendance_import_rows": attendance_import_rows, "dispatches": dispatches,
    }
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} with {len(products)} products, {len(results)} results, {len(attendance)} attendance records, {len(defects)} defects, and {len(quality_reviews)} quality reviews.")


if __name__ == "__main__":
    main()

