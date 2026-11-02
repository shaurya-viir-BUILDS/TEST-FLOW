# TestFlow Operations & Quality Assurance Frontend Console

A responsive, high-performance web console for the TestFlow Electronics Testing, QA & Traceability Platform.

## Features
- **Design System & Theme**: High-precision White Smoke (`#F0F0F0`) and Bright Red (`#E7473C`) industrial palette with design tokens, component classes (`.tf-btn`, `.tf-input`, `.tf-table`, `.tf-kpi`), and accessible keyboard focus outlines.
- **Dedicated Sign-In Page**: Accessible at `/login` with full authentication credential directory and 1-click login for all 7 platform roles.
- **Responsive Mobile Navigation**: Slide-over drawer with hamburger button, backdrop scrim, and keyboard escape dismiss.
- **Role-Based Persona Switcher**: Instant 1-click authentication as Operations Manager, QA Inspector, Store Keeper, Test Lead, Test Technician, Super Admin, or HR Officer.
- **Operations & Yield Dashboard**: Real-time First-Pass Yield (FPY) rates, test outcome doughnut distribution, and top defect Pareto bar charts using Chart.js.
- **Technician Testing Workbench**: Live assigned queues with automated tolerance checklist runners for manual inspection and automated bench CSV ingestion.
- **Quality Assurance & Disposition Flow**: Active defect incident tracking with QA disposition sign-offs (APPROVE, RETEST, SCRAP) enforcing strict quality gates.
- **Batches & Serialization Master**: Inward lot tracking, batch progress analytics with yield percentages, and serialization visibility.
- **Outbound Dispatch Registry**: Outbound dispatch orders enforcing per-unit QA approval gates before shipment.
- **Universal Traceability Query**: Complete digital birth-to-dispatch certificate timeline for any electronics serial number (e.g. `SYN-TF-0017`).
- **HR & Shift Attendance**: Shift roll call with live punch-in/out check-in functionality.

## Architecture
- **Tech Stack**: Vanilla ES6 Modules + Tailwind CSS v3 + Chart.js + Lucide Icons + Font Inter.
- **Zero Build Friction**: Runs directly in any modern browser without requiring Node.js or bundlers.
- **FastAPI Integration**: Automatically mounted and served by the FastAPI backend at `http://127.0.0.1:8000/`.

