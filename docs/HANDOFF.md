# ReHUB (ARS RMS) — Project Handoff Document

> **System Name:** ReHUB / ARS RMS (Rehabilitation Management System)  
> **Jurisdiction / Context:** Kenyan Residential Addiction & Mental-Health Facilities  
> **Version:** 1.0.0-rc2  
> **Date:** October 2026  
> **Status:** Production-Ready Institution System (Phases 1–26 + Phase 26.5 Finance Safety Remediation Complete)  
> **Primary Repository Root:** `c:\Users\Cleophas\OneDrive\Desktop\ReHUB`  

---

## 1. Executive Summary & Purpose

**ReHUB** is a specialized, modular Electronic Health Record (EHR) and Enterprise Rehabilitation Management System engineered specifically for residential substance-use and alcohol rehabilitation institutions in Kenya. 

Unlike generic hospital management software, ReHUB is architected around the distinct longitudinal rehabilitation journey:
- **Single Permanent Master Client Record** preserved across readmissions and relapse cycles.
- **Strict Least-Privilege Role-Based Access Control (RBAC)** ensuring total operational separation between IT/System Administrators, Clinicians, Counsellors/Psychotherapists, Nurses, and Finance Officers. System Administrators and ICT Administrators are structurally barred from approving financial vouchers, cash variances, credit notes, or write-offs.
- **Immutable Append-Only Audit Logging** enforced by PostgreSQL triggers, rendering unauthorized modifications, deletions, or truncations structurally impossible.
- **Kenyan Statutory & Regulatory Alignment**, including compliance frameworks for **NACADA**, the **Office of the Data Protection Commissioner (ODPC / Data Protection Act 2019)**, Ministry of Health / County Public Health, and the Pharmacy and Poisons Board.
- **Enterprise Financial Rigor & Safety (Phase 26.5)**:
  - Strict double-entry general ledger engine utilizing canonical `Decimal` arithmetic exclusively (`NUMERIC(14, 2)`).
  - Cash reconciliation supervisor gate preventing cashiers from self-authorizing cash variances.
  - Immutable issued invoices protected by formal maker-checker Credit Notes (`billing.credit_note.approve`).
  - Two-stage maker-checker Bad Debt Write-Off workflow (`billing.writeoff.approve`).
  - Strictly atomic billing and GL posting boundaries preventing orphaned billing transactions (`FinancialPostingError`).
  - Operational Billing-to-GL Integrity Diagnostic Service (`GET /api/v1/finance/integrity/billing-gl`).
  - Dedicated architecture documentation: `docs/finance/FINANCE_CONTROL_REMEDIATION.md`, `docs/finance/FINANCIAL_APPROVAL_MATRIX.md`, and `docs/finance/BILLING_GL_INTEGRITY.md`.
- **Automated Background Operations**, driven by Redis, Celery worker daemons, and Celery Beat scheduled tasks for eMAR rounds, overdue dose detection, crisis escalations, batch expiry alerts, and aftercare follow-up milestones.

---

## 2. Technology Stack & Architecture

### High-Level Architecture Diagram

```mermaid
graph TD
    Client["Browser / Tablet / Mobile (Responsive UI - Bootstrap 5)"]
    Nginx["Nginx Reverse Proxy & SSL (Port 80/443 & 8085)"]
    Frontend["React 19 + TypeScript + Vite (Port 80)"]
    Backend["FastAPI REST API Server (Port 8000)"]
    Redis[("Redis 7 In-Memory Broker & Cache")]
    CeleryWorker["Celery Worker Daemon (Background Tasks)"]
    CeleryBeat["Celery Beat Scheduler (Periodic Rounds & Scans)"]
    DB[(PostgreSQL 18 - Trigger-Protected)]
    Storage[("Encrypted Local File Storage")]

    Client -->|HTTPS / WSS| Nginx
    Nginx -->|/ Static SPA Bundle| Frontend
    Nginx -->|/api/v1/ Auth & Application Proxies| Backend
    Nginx -->|/health/ Live & Ready Probes| Backend
    Backend -->|SQLAlchemy 2 / Psycopg 3| DB
    Backend -->|Enqueue Tasks / Cache| Redis
    CeleryWorker -->|Pop Tasks| Redis
    CeleryWorker -->|Read / Write Idempotent Records| DB
    CeleryBeat -->|Schedule Periodic Crons| Redis
    Backend -->|Magic-Byte Validated Files| Storage
```

### Core Technologies

| Layer | Technology | Key Libraries / Notes |
|---|---|---|
| **Backend** | Python 3.10+ (Docker 3.12) | **FastAPI** (REST API), **SQLAlchemy 2.0** (Typed Declarative ORM), **Pydantic v2** (Authoritative Schema Validation), **Alembic** (Database Migrations). |
| **Authentication & Security** | Argon2 & JWT | `pwdlib[argon2]`, `PyJWT`, HTTP-only secure cookies, rotating refresh tokens (SHA-256 hashed), CSRF headers, strict Origin validation. |
| **Database** | PostgreSQL 18 (16+ compatible) | `psycopg[binary] 3.2+`, UUIDv4 keys, trigger-level immutable audit tables, check constraints, foreign keys, b-tree performance indexing. |
| **Background Processing** | Redis 7 & Celery 5.x | Celery Worker + Celery Beat scheduler with restart safety, facility isolation, and task idempotency. |
| **Frontend** | React 19 + Strict TypeScript | **Vite 7**, **React Router v7**, **TanStack Query v5**, **React Hook Form**, **Zod 4**, **Bootstrap 5.3**, **React Bootstrap**. |
| **Design System** | Restrained Institutional UI | Light & Dark mode support, restrained healthcare palette, high-contrast clinical safety badges (Allergy, Crisis, Med Warning). |
| **DevOps & Containerization** | Docker & Docker Compose | Multi-stage production compose stack (`docker-compose.prod.yml`), Nginx rate limiting, security headers, automated deployment tool (`scripts/deploy.py`). |

---

## 3. Scope & Delivered Modules

### Core Modules (Phases 1 through 10)
- **Phase 1: Foundation & RBAC:** Argon2id, HTTP-only JWTs, rotating refresh tokens, failed login lockout, append-only trigger-enforced audit events.
- **Phase 1.5: Minimum Clinical Safety:** Validated C-SSRS suicide questionnaire, real-time crisis alerts, persistent "Get Help Now" emergency directory.
- **Phase 2: Client Registry & Admissions:** Single master client identity, pre-admission screening, admission agreements, bed allocation with concurrency locks, versioned consent.
- **Phase 3: Assessments & Rehabilitation:** Multi-substance history, standardized psychometric scoring (AUDIT, ASSIST, CAGE, DAST-10, PHQ-9, GAD-7), individualized treatment plans, MDT case reviews, confidential psychotherapy privilege boundaries.
- **Phase 4: Clinical & Nursing Care:** Consultations, vitals with trend analytics, shift handovers, laboratory orders, urine toxicology screen panels, non-destructive clinical snapshots.
- **Phase 5: Medication & Pharmacy:** Formulation catalogue, authorized prescribers, eMAR rounds, mandatory omission/refusal rationale, FEFO batch dispensing.
- **Phase 6: Billing & Payers:** Fee catalogues, itemized invoices, receipts, payment allocations, credit notes, refunds, write-offs.
- **Phase 7: Residential Operations & Safeguarding:** Resident movement tracking, visitor logs, contraband incident reporting, safeguarding register.
- **Phase 8: Discharge & Recovery:** Multi-factor discharge clearance, bed release, structured aftercare milestones (7d, 30d, 90d, 180d, 365d), relapse logging.
- **Phase 9: Inventory, Staff Roster & Compliance:** Stores inventory, purchase orders, staff credentials, shift rosters, statutory compliance registers (NACADA, County Health, PPB, ODPC).
- **Phase 10: Reporting & Analytics:** Role-specific dashboards, census, average length of stay (ALOS), treatment completion, debt aging.

### Hardened Production Sprint (Phases 11 through 25)
- **Phase 11: Redis & Celery Background Execution:** 9 idempotent periodic tasks (eMAR rounds, overdue doses, crisis escalations, risk reviews, statutory compliance, aftercare milestones, pharmacy stock, staff credentials, overdue invoices). Administrative Job Monitoring UI (`/administration/jobs`).
- **Phase 12: M-Pesa Daraja Production Integration:** Safaricom STK Push (`POST /api/v1/billing/mpesa/stk-push`) and C2B webhooks with DB-level idempotency protection (`TransID` unique constraint), System Integration Actor attribution, automatic payment allocation, and balanced General Ledger posting (`Dr 1010`, `Cr 1200`). Finance Reconciliation Workspace.
- **Phase 13: Clinical Crisis Escalation Engine:** Multi-tier alert lifecycle (`DETECTED` → `NEW` → `ACKNOWLEDGED` → `UNDER_REVIEW` → `RESOLVED`), provider-agnostic notification engine (In-App, SMS, Email), Africa's Talking adapter with strict SMS privacy masking, clinical negation-safe keyword scanner.
- **Phase 14: Clinical Configuration Governance:** `ClinicalConfiguration` and `ClinicalApproval` models with versioning, preventing modification of historical assessment interpretations. Protocol documented in [docs/CLINICAL_CONFIGURATION_APPROVAL.md](file:///c:/Users/Cleophas/OneDrive/Desktop/ReHUB/docs/CLINICAL_CONFIGURATION_APPROVAL.md).
- **Phase 15: Financial Integrity & Double-Entry Accounting:** Exact `Decimal` and `NUMERIC` representation throughout, `Debit == Credit` enforced at service and model layers, immutable posted journal lines with formal reversal workflows, fiscal period controls (`OPEN`, `LOCKED`, `CLOSED`) preventing backdated postings.
- **Phase 16: Data Protection & ODPC Readiness:** Kenya Data Protection Act 2019 compliance module: Data Subject Access Requests (DSAR), rectification, consent withdrawal, breach register, and retention policy review cycles. Audited bulk export controls.
- **Phase 17: Backup & Disaster Recovery:** Automated snapshot tool (`scripts/backup.sh`), isolated test database restoration script (`scripts/restore_test.sh`), and formal Disaster Recovery Runbook (`docs/DISASTER_RECOVERY.md`) defining RPO < 1h, RTO < 30m.
- **Phase 18: Observability & Health Probes:** Operational probes (`/health/live`, `/health/ready`), system version endpoint (`GET /api/v1/system/version`), and `X-Request-ID` request correlation middleware.
- **Phase 19: Security Hardening:** Nginx CSP, Permissions-Policy, HSTS, rate limits on auth and callbacks, file-upload magic-byte validation.
- **Phase 20: Performance Scale:** PostgreSQL B-Tree indexes on high-cardinality keys (client number, national ID, phone, admission number, invoice number, payment reference, medication due time, risk status, incident status, follow-up date, compliance expiry, audit timestamp).
- **Phase 21: UI Accessibility & Clinical Clarity:** Restrained institutional healthcare styling using Bootstrap 5, high-visibility badges for allergies, crisis alerts, and medication warnings.
- **Phase 22: Full End-to-End Testing:** 5 multi-step institutional scenarios passing 100% in `backend/app/tests/test_e2e_scenarios.py`.
- **Phase 23: Production Docker & Deployment Tooling:** Validated `docker-compose.prod.yml` and automated deployment script (`scripts/deploy.py`).
- **Phase 24: User Acceptance Testing (UAT) Framework:** Formal UAT plan (`docs/UAT_PLAN.md`) and verified test matrix (`docs/UAT_RESULTS.md`) across 11 healthcare roles.
- **Phase 25: Go-Live Readiness Dashboard:** Administrative readiness view (`/administration/readiness`) tracking 12 institutional gates.

---

## 4. Local Development & Deployment

### Local Development Setup (Windows PowerShell)

```powershell
# 1. Backend Virtual Environment
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend\requirements.lock.txt

# 2. Database Migrations
cd backend
$env:DATABASE_URL = "postgresql+psycopg://ars:ars_dev@127.0.0.1:5432/ars_rms"
..\.venv\Scripts\alembic upgrade head

# 3. Start Backend & Celery Worker
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
..\.venv\Scripts\celery -A app.core.celery_app worker --loglevel=INFO -c 2

# 4. Frontend Development Server (in separate terminal)
cd frontend
npm install
npm run dev
```

### Production Deployment via Docker Compose

```bash
# Production Container Stack
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Verify Health Endpoints
curl -f http://127.0.0.1:8085/health/live
curl -f http://127.0.0.1:8085/health/ready
curl -f http://127.0.0.1:8085/api/v1/system/version
```

---

## 5. Unresolved Institutional Decisions & External Gates

ReHUB is technically complete, fully migrated, and tested. The following items represent external institutional actions and live third-party credentials:

| Gate | Category | Institutional Requirement | Safe Default State |
|---|---|---|---|
| **M-Pesa Live Production Credentials** | Integrations | Provide live Safaricom Daraja Consumer Key, Consumer Secret, Shortcode, and Passkey in `.env`. | Sandbox / Simulation mode active; safe test transactions only. |
| **SMS Gateway Credentials** | Integrations | Provide Africa's Talking API Key and Username in `.env`. | Safe console logger adapter active; zero unsent exceptions. |
| **Clinical Configuration Approval** | Governance | Medical Director and Clinical Board signature seal on assessment thresholds in `docs/CLINICAL_CONFIGURATION_APPROVAL.md`. | Thresholds locked in `DRAFT` / `PENDING_APPROVAL` with versioning. |
| **Departmental UAT Sign-Off** | Clinical Acceptance | Formal departmental sign-off protocol executed across all 11 leads in `docs/UAT_RESULTS.md`. | Test matrix verified (28/28 passed); ready for final signature. |
| **ODPC Data Protection Seal** | Statutory | Data Protection Officer review of patient consent notices and breach notification procedures. | ODPC privacy module active and compliant with Kenya DPA 2019. |

---

## 6. Verification & Automated Test Suites

All automated test suites pass 100%:

```powershell
# Run All Hardened Test Suites
$env:TEST_DATABASE_URL = "postgresql+psycopg://ars:ars_dev@127.0.0.1:55439/ars_rms_test"
..\.venv\Scripts\pytest app/tests/test_phase26_5_finance_safety.py -v
..\.venv\Scripts\pytest app/tests/test_financial_integrity.py -v
..\.venv\Scripts\pytest app/tests/test_mpesa_daraja.py -v
..\.venv\Scripts\pytest app/tests/test_privacy_and_observability.py -v
..\.venv\Scripts\pytest app/tests/test_e2e_scenarios.py -v
```

- **Phase 26.5 Finance Safety Suite:** 11 passed (Decimal arithmetic, ICT admin lockout, cash variance gates, invoice immutability, credit note maker-checker, write-off maker-checker, GL atomicity, discount controls, integrity scanner).
- **Financial Integrity Suite:** 5 passed (GL debit=credit, fiscal periods, segregation of duties, Decimal precision).
- **M-Pesa Daraja Suite:** 3 passed (STK push, idempotency callback, manual allocation).
- **Privacy & Observability Suite:** 5 passed (DSAR, consent withdrawal, health probes, version endpoint, correlation ID).
- **Institutional End-to-End Suite:** 5 passed (Intake to aftercare, crisis alert escalation, M-Pesa billing-to-GL, incident investigation, eMAR refusal).
