# TestFlow: Integrated Electronics Testing, QA & Operations Management Platform

[![Project Status: Backend Implemented](https://img.shields.io/badge/Status-Backend%20Implemented-green.svg)](#)
[![Architecture: Option B](https://img.shields.io/badge/Stack-FastAPI%20%2B%20React%20%2B%20PostgreSQL-green.svg)](#)
[![Academic Project](https://img.shields.io/badge/Project-Internship%20Major%20Project-purple.svg)](#)

---

## 1. Overview

**TestFlow** is a centralized operations and quality management platform designed for electronics testing, refurbishing, and manufacturing facilities handling products such as **Wi-Fi routers, remote controls, set-top boxes (STBs), and IoT gateways**.

In typical testing facilities, operational records are heavily fragmented across physical paper traveler sheets, disparate Excel workbooks, and standalone test machine outputs. TestFlow eliminates operational silos by unifying **HR/Shift attendance**, **batch & serial inventory**, **configurable testing & QA execution**, and **dispatch traceability** into a single, cohesive web platform.

---

## 2. Core Modules

| # | Module | Scope & Responsibilities |
| :--- | :--- | :--- |
| **1** | **Employee & HR Management** | Employee profiles, department mapping, role permissions, daily check-in/out, biometric Excel import, and shift availability. |
| **2** | **Client & Product Catalog** | Client organizations, product categories (Routers, STBs, Remotes), model specifications, and testing criteria definitions. |
| **3** | **Batch & Inventory Management** | Inward lot receiving, serial number registration / bulk generation, QR labeling, batch staging, and unit status tracking. |
| **4** | **Testing Management** | Configurable test parameter templates, technician manual checklist execution, and automated bench CSV/Excel log imports. |
| **5** | **Quality Assurance & Defect Tracking**| Defect logging with severity/code categorization, QA approval, retest routing, and quarantine management. |
| **6** | **Dispatch & Traceability** | Dispatch challan generation, packing verification, and full end-to-end serial lifecycle audit history. |
| **7** | **Dashboards & Operational Analytics**| Real-time yield percentages, batch completion bars, technician throughput, and defect Pareto breakdowns. |

---

## 3. Technology Stack (Option B)

* **Backend:** Python 3.11+ with **FastAPI**
  * **ORM & Database Abstraction:** SQLAlchemy 2.0 + Alembic (migrations)
  * **Validation & Serialization:** Pydantic v2
  * **File Parsers:** `pandas` & `openpyxl` (biometric Excel attendance & automated bench CSVs)
  * **API Docs:** Interactive Swagger UI (`/docs`) and ReDoc (`/redoc`)
* **Database:** **PostgreSQL** (with SQLite support for zero-friction local development)
* **Frontend:** **React 18** (Vite) + **TypeScript**
  * **UI Framework:** Tailwind CSS + Shadcn UI primitives + Lucide Icons
  * **State & Data Fetching:** TanStack Query (React Query) + Axios
* **Authentication:** JWT (JSON Web Tokens) with HTTP-only cookies and Role-Based Access Control (RBAC).

---

## 4. Repository Structure

```
testflow/
├── README.md                 # Project introduction and overview
├── AGENTS.md                 # Engineering guidelines and architectural guardrails for AI agents
├── docs/                     # Comprehensive engineering planning documentation
│   ├── requirements.md       # Detailed functional & non-functional requirements
│   ├── architecture.md       # High-level architecture, ingestion pipeline & security
│   ├── data-model.md         # Schema definitions, ERD, and state machine flows
│   ├── api-contract.md       # OpenAPI / RESTful endpoint specifications
│   └── roadmap.md            # Phased development milestones and risk management
├── backend/                  # FastAPI backend application (Phase 1)
└── frontend/                 # React + Vite frontend application (Phase 1)
```

---

## 5. Documentation Quick Links

* 📄 [Functional & Non-Functional Requirements](docs/requirements.md)
* 🏗️ [System Architecture & Ingestion Design](docs/architecture.md)
* 🗄️ [Data Model, ERD & State Machines](docs/data-model.md)
* 🌐 [REST API Contract & Endpoints](docs/api-contract.md)
* 🗺️ [Development Roadmap & Milestones](docs/roadmap.md)
* 🤖 [AI Agent Guidelines & Guardrails](AGENTS.md)

---

## 6. Current Status & Next Steps

The platform is fully implemented with:
- **FastAPI backend**: Authentication, RBAC, catalogs, batches, manual/bench testing engine, QA review, outbound dispatch, and analytics. Interactive OpenAPI documentation is at `/docs`.
- **Integrated Web Console frontend**: Pure modern HTML5/ES modules UI located in `/frontend`, mounted automatically at `http://127.0.0.1:8000/` and `/static/login.html`.

### Local run (Backend & Frontend Console)

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# For local development with SQLite (default):
python -m app.db.seed                 # Seeds staff accounts (Shaurya Viir Singh & Sambhav Yadav)
python -m app.db.load_synthetic_seed  # Seeds 120-unit relational test demo dataset
uvicorn app.main:app --reload --app-dir .
```
Access the web console at `http://127.0.0.1:8000/` (or `http://127.0.0.1:8000/static/login.html`).

### Production & PostgreSQL Migration Order

For PostgreSQL staging or production, set `POSTGRES_URL` (or `DATABASE_URL`) and `ENVIRONMENT=production`. **Always run migrations before seeding**:

```bash
cd backend
# 1. Apply baseline Alembic database migration first
alembic upgrade head

# 2. Run initial administrative bootstrap (if needed)
ALLOW_SEED_IN_PRODUCTION=true python -m app.db.seed
```

### Security & Production Guardrails
- `SECRET_KEY` is mandatory when `ENVIRONMENT=production` and must not use known insecure dev defaults.
- Default SQLite is blocked in production; a PostgreSQL URI is required.
- Public 1-click demo personas and credential listings are automatically disabled in production mode.
- In local development, demo accounts are:
  - **Operations Manager**: `sambhav.yadav@testflow.local` / Password: `12345` (Sambhav Yadav)
  - **Super Admin**: `shaurya.singh@testflow.local` / Password: `67890` (Shaurya Viir Singh)

