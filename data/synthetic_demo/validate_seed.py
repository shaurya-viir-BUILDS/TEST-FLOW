#!/usr/bin/env python3
"""Validate the neutral TestFlow synthetic seed against documented invariants."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
DATA = json.loads((ROOT / "seed_data.json").read_text(encoding="utf-8"))
errors = []

employees = {x["employee_id"]: x for x in DATA["employees"]}
clients = {x["client_id"]: x for x in DATA["clients"]}
models = {x["model_id"]: x for x in DATA["product_models"]}
templates = {x["template_id"]: x for x in DATA["test_templates"]}
batches = {x["batch_id"]: x for x in DATA["batches"]}
products = {x["product_id"]: x for x in DATA["products"]}
assignments = {x["assignment_id"]: x for x in DATA["test_assignments"]}
results = {x["result_id"]: x for x in DATA["test_results"]}

def check(condition, message):
    if not condition:
        errors.append(message)

# Required cardinalities and synthetic labeling.
check(len(employees) == 14, f"expected 14 employees, got {len(employees)}")
check(any(e["role"] == "qa" for e in employees.values()), "missing QA inspector employee")
check(any(e["role"] == "store_keeper" for e in employees.values()), "missing store keeper employee")
check(len(clients) == 3, f"expected 3 clients, got {len(clients)}")
check(len(models) == 6, f"expected 6 product models, got {len(models)}")
check(len(templates) == 4, f"expected 4 templates, got {len(templates)}")
check(len(batches) == 8, f"expected 8 batches, got {len(batches)}")
check(len(products) == 120, f"expected 120 products, got {len(products)}")
check(20 <= len(DATA["defects"]) + len(DATA["quality_reviews"]) <= 30, "defects + quality reviews must be 20-30")
check(DATA["dataset_metadata"]["label"] == "SYNTHETIC_DEMO", "dataset is not clearly labeled synthetic")
check(len({p["serial_number"] for p in DATA["products"]}) == 120, "serial numbers are not unique")
check(all(p["serial_number"].startswith("SYN-") for p in DATA["products"]), "a serial number is not clearly synthetic")

# Foreign keys and model/template relationships.
for m in models.values():
    check(m["client_id"] in clients, f"model {m['model_id']} has invalid client")
    check(m["test_template_id"] in templates, f"model {m['model_id']} has invalid template")
for b in batches.values():
    check(b["model_id"] in models, f"batch {b['batch_id']} has invalid model")
for p in products.values():
    check(p["batch_id"] in batches, f"product {p['product_id']} has invalid batch")
    check(p["model_id"] in models, f"product {p['product_id']} has invalid model")
    check(p["model_id"] == batches[p["batch_id"]]["model_id"], f"product {p['product_id']} model does not match batch")
for a in assignments.values():
    check(a["product_id"] in products, f"assignment {a['assignment_id']} has invalid product")
    check(a["template_id"] in templates, f"assignment {a['assignment_id']} has invalid template")
    check(a["assigned_to_employee_id"] in employees, f"assignment {a['assignment_id']} has invalid tester")
    expected = models[products[a["product_id"]]["model_id"]]["test_template_id"]
    check(a["template_id"] == expected, f"assignment {a['assignment_id']} uses wrong template")
for r in results.values():
    check(r["assignment_id"] in assignments, f"result {r['result_id']} has invalid assignment")
    check(r["product_id"] == assignments[r["assignment_id"]]["product_id"], f"result {r['result_id']} product mismatch")
    template_steps = {s["step_id"]: s for s in templates[assignments[r["assignment_id"]]["template_id"]]["steps"]}
    check(r["step_id"] in template_steps, f"result {r['result_id']} has invalid step")
    step = template_steps[r["step_id"]]
    if r["status"] == "pass":
        v = r["measurement_value"]
        check(v is not None and step["valid_range"]["min"] <= v <= step["valid_range"]["max"], f"passing result {r['result_id']} is outside range")
    if r["status"] == "fail":
        check(r["measurement_value"] is not None and (r["measurement_value"] < step["valid_range"]["min"] or r["measurement_value"] > step["valid_range"]["max"]), f"failed result {r['result_id']} is not out of range")

# Batch quantities exactly match registered products.
counts = Counter(p["batch_id"] for p in products.values())
for b in batches.values():
    check(counts[b["batch_id"]] == b["quantity"], f"batch {b['batch_id']} quantity mismatch")
check(counts["BAT-SYN-001"] == 0, "empty awaiting-registration batch is not empty")

# Status coherence: pending/retest/rejected paths, no unresolved failure on passed product.
results_by_product = defaultdict(list)
for r in results.values():
    results_by_product[r["product_id"]].append(r)
defects_by_product = defaultdict(list)
for defect in DATA["defects"]:
    check(defect["product_id"] in products, f"defect {defect['defect_id']} has invalid product")
    defects_by_product[defect["product_id"]].append(defect)
for p in products.values():
    rs = results_by_product[p["product_id"]]
    statuses = {r["status"] for r in rs}
    if p["status"] == "pending":
        check("pending" in statuses, f"pending product {p['product_id']} lacks pending result")
    if p["status"] == "failed_awaiting_retest":
        check("fail" in statuses, f"retest product {p['product_id']} lacks failed result")
        check(any(d["status"] == "awaiting_retest" for d in defects_by_product[p["product_id"]]), f"retest product {p['product_id']} lacks awaiting-retest defect")
    if p["status"] == "passed":
        check("fail" not in statuses and "pending" not in statuses, f"passed product {p['product_id']} has unresolved result")
        check(all(d["status"] == "resolved" for d in defects_by_product[p["product_id"]]), f"passed product {p['product_id']} has unresolved defect")
    if p["status"] == "rejected":
        check(any(d["status"] == "closed_rejected" for d in defects_by_product[p["product_id"]]), f"rejected product {p['product_id']} lacks rejection defect")

# Quality review references and dispatch eligibility.
for q in DATA["quality_reviews"]:
    check(q["batch_id"] in batches, f"quality review {q['quality_review_id']} has invalid batch")
    check(q["reviewed_by_employee_id"] in employees, f"quality review {q['quality_review_id']} has invalid reviewer")
    check(employees[q["reviewed_by_employee_id"]]["role"] == "qa", f"quality review {q['quality_review_id']} is not attributed to a QA inspector")
for dispatch in DATA["dispatches"]:
    check(dispatch["batch_id"] in batches, f"dispatch {dispatch['dispatch_id']} has invalid batch")
    for pid in dispatch["product_ids"]:
        check(pid in products, f"dispatch {dispatch['dispatch_id']} has invalid product")
        p = products[pid]
        approved = any(q["batch_id"] == p["batch_id"] and q["status"] == "approved" for q in DATA["quality_reviews"])
        check(p["status"] == "passed" and approved, f"dispatch {dispatch['dispatch_id']} includes ineligible product {pid}")

# Attendance references, date validity, and invalid import rows.
valid_attendance_statuses = {"present", "absent", "late", "leave", "half_day"}
for a in DATA["attendance_records"]:
    check(a["employee_id"] in employees, f"attendance {a['attendance_id']} has invalid employee")
    try:
        date.fromisoformat(a["attendance_date"])
    except ValueError:
        errors.append(f"attendance {a['attendance_id']} has invalid date")
    check(a["status"] in valid_attendance_statuses, f"attendance {a['attendance_id']} has invalid status")
for row in DATA["attendance_import_rows"]:
    check(row["valid"] is False and row.get("error"), f"invalid import row {row['row_id']} not marked with error")

# Required edge cases.
statuses = {b["lifecycle_status"] for b in batches.values()}
check("awaiting_registration" in statuses, "missing empty awaiting-registration batch")
check("partially_tested" in statuses, "missing partially tested batch")
check(any(p["status"] == "failed_awaiting_retest" for p in products.values()), "missing failed item awaiting retest")
check(any(p["status"] == "rejected" for p in products.values()), "missing rejected item")
check(len(DATA["attendance_import_rows"]) >= 1, "missing invalid attendance import rows")

if errors:
    print("VALIDATION FAILED")
    print("\n".join(f"- {e}" for e in errors))
    sys.exit(1)

print("VALIDATION PASSED")
print(f"employees={len(employees)} clients={len(clients)} models={len(models)} templates={len(templates)} batches={len(batches)} products={len(products)}")
print(f"assignments={len(assignments)} results={len(results)} defects={len(DATA['defects'])} quality_reviews={len(DATA['quality_reviews'])} attendance={len(DATA['attendance_records'])} dispatches={len(DATA['dispatches'])}")
print(f"product_statuses={dict(Counter(p['status'] for p in products.values()))}")
print(f"result_statuses={dict(Counter(r['status'] for r in results.values()))}")
print(f"attendance_statuses={dict(Counter(a['status'] for a in DATA['attendance_records']))}")

