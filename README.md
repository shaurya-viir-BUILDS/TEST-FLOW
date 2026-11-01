# TestFlow: Integrated Electronics Testing, QA & Operations Management Platform

[![Project Status: Planning](https://img.shields.io/badge/Status-Planning%20%26%20Specification-blue.svg)](#)
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

This project is currently in the **Planning & Documentation Phase**. Implementation will proceed strictly in accordance with [docs/roadmap.md](docs/roadmap.md):
1. **Milestone 1:** Repository initialization, database setup, Auth & HR attendance management.
2. **Milestone 2:** Client, Product Model & Inward Batch / Serialization tracking.
3. **Milestone 3:** Test Templates, Manual & Automated CSV Test Execution, and QA Dispositions.
4. **Milestone 4:** Dispatch Management, Universal Serial Traceability, and Analytics Dashboards.
5. **Milestone 5:** Realistic electronics seed data, edge-case testing, and academic defense preparation.

