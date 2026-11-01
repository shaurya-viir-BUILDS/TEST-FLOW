# AGENTS.md: Developer & AI Agent Guidelines for TestFlow

> **Scope Note for AI Assistants & Contributors:**
> This repository houses **TestFlow**, an undergraduate internship major project. Follow the engineering standards, scope limits, and operational assumptions documented herein.

---

## 1. Prime Directives & Hard Constraints

1. **Do NOT Invent Hardware / Equipment Integrations:**
   * Do **NOT** implement direct TCP/IP sockets, serial ports (`RS-232`), MODBUS, or live machine drivers to test equipment.
   * Testing machines are treated strictly as **file-producing external systems**. Automated test ingestion must only occur via file uploads (standard `.csv` or `.xlsx` files) exported by test benches.
2. **Do NOT Assume Automated OCR / Paper Scanning:**
   * Paper traveler job-cards are a real-world reality in the target company, but automated scanning/OCR is out-of-scope for v1.
   * Provide clean, intuitive manual entry forms and file imports instead of speculative OCR pipelines.
3. **Preserve Relational Integrity & Traceability:**
   * Every tested unit (`BatchItem`) must link immutably back to its parent `Batch`, `ProductModel`, and `Client`.
   * Test results and QA dispositions must record the exact `Employee` (technician or inspector) and timestamp. Never allow orphaned test sessions.
4. **Adhere to the Selected Tech Stack (Option B):**
   * **Backend:** Python 3.11+ with **FastAPI**, **SQLAlchemy 2.0**, and **Pydantic v2**.
   * **Database:** **PostgreSQL** in production/staging; **SQLite** acceptable for local standalone unit test harnesses.
   * **Frontend:** **React 18** with **Vite**, **TypeScript**, and **Tailwind CSS**.
   * Do **NOT** switch to alternative frameworks (e.g., Django, NestJS) without explicit user authorization.

---

## 2. Unresolved Company Questions & Assumptions (DO NOT ASSUME)

When authoring code or schemas, leave flexibility for the following unresolved client-specific workflows:

* **[OPEN-Q1] Serial Number Inward Strategy:**
  * *Context:* Whether incoming shipments already have vendor barcode stickers or if the facility prints its own internal QR stickers.
  * *Code Rule:* The batch inwarding schema must support **both**: bulk entering existing vendor serial numbers (via list/CSV) OR auto-generating sequential internal serials (e.g., `TF-{YYMM}-{BATCH}-{SEQ}`).
* **[OPEN-Q2] Automated Test Bench Log Format:**
  * *Context:* The exact column headers produced by bench computers (e.g., RF tester, Ping tester) are unconfirmed.
  * *Code Rule:* The CSV/Excel parser must use an adaptable mapping strategy or validate against a standard canonical schema (`serial_number`, `parameter_name`, `measured_value`, `result`, `timestamp`).
* **[OPEN-Q3] Biometric Attendance Export Format:**
  * *Context:* Biometric attendance hardware exports varying column structures across vendors.
  * *Code Rule:* The attendance upload service must be tolerant of common column aliases (e.g., `EmpId`, `Employee_Code`, `Staff_ID`, `In_Time`, `Punch_In`).
* **[OPEN-Q4] 100% Testing vs. AQL Sampling:**
  * *Context:* High-value routers often undergo 100% testing, while low-cost remote controls may use statistical AQL sampling.
  * *Code Rule:* The QA disposition engine must allow individual unit disposition as well as batch-level sign-offs.

---

## 3. Code Organization & Standards

### 3.1 Backend (FastAPI)
```
backend/
├── app/
│   ├── api/
│   │   └── v1/                  # Versioned API route controllers
│   ├── core/                    # Config, security, database session, exceptions
│   ├── models/                  # SQLAlchemy ORM database models
│   ├── schemas/                 # Pydantic v2 request/response schemas
│   ├── services/                # Business logic & file parsers (CSV/Excel)
│   └── tests/                   # Pytest suite
├── alembic/                     # Database migrations
└── pyproject.toml / requirements.txt
```

* **Naming Conventions:**
  * Database tables: `plural_snake_case` (e.g., `batch_items`, `test_sessions`).
  * Pydantic schemas: `PascalCase` with descriptive suffixes (e.g., `BatchCreate`, `BatchResponse`).
  * Route endpoints: `kebab-case` with plural resource names (e.g., `/api/v1/test-templates`).
* **Error Handling:**
  * Always return standard JSON error envelopes with structured error codes:
    ```json
    {
      "detail": {
        "code": "INVALID_SERIAL_STATUS",
        "message": "Unit SN-1002 is not in ALLOCATED state."
      }
    }
    ```

### 3.2 Frontend (React + Vite + TypeScript)
```
frontend/
├── src/
│   ├── assets/
│   ├── components/
│   │   ├── ui/                  # Shadcn / core reusable primitives
│   │   └── shared/              # Navbar, sidebar, data tables, modals
│   ├── features/                # Domain-driven feature slices (auth, batches, testing, qa)
│   ├── hooks/                   # Custom React hooks
│   ├── services/                # API client (Axios / TanStack Query)
│   ├── types/                   # TypeScript interfaces matching backend schemas
│   └── App.tsx
```

---

## 4. Verification & Testing Guardrails

* Every PR or milestone delivery must include:
  1. Passing backend unit tests (`pytest`).
  2. Pydantic schema validation tests for file upload parsers (Excel attendance & bench CSVs).
  3. Clean TypeScript compilation (`tsc --noEmit`) with zero unresolved `any` types.
* Pre-configured seed data must populate realistic test records (e.g., 50–100 Wi-Fi routers and remotes across different stages) to ensure the platform is ready for demonstration at any moment.

