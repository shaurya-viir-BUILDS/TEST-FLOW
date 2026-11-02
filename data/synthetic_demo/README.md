# TestFlow Synthetic Demo Seed

This directory contains the official **TestFlow Synthetic Demo Seed Dataset** for electronics testing, quality assurance, and operations management.

## Files

- `seed_data.json` — Generated seed payload containing all entities and relationships.
- `generate_seed.py` — Deterministic generator; rerunning it resets the JSON to the same dataset.
- `validate_seed.py` — Consistency checks for counts, foreign keys, quantities, test-template mapping, failure paths, attendance, and dispatch eligibility.

## Invariant Summary

- 14 Employees (Management, HR, Test Lead, Tester, QA Inspector, Store Keeper)
- 3 Clients (Northstar Signal Works, Blue Orbit Devices, Cedar Loop Electronics)
- 6 Product Models (Wi-Fi Routers, Remotes, Set-Top Boxes)
- 4 Configurable Test Templates with tolerance ranges
- 8 Batches with lifecycle statuses
- 120 Individually tracked units (Serial numbers `SYN-TF-0001` through `SYN-TF-0120`)
- 120 Test Assignments with step-level measurements
- Defect records with severity, categories, and resolution
- Quality Reviews (batch-level QA decisions)
- Attendance records for August–October 2026
- Dispatch records with strict QA approval validation

