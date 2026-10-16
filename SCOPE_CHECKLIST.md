# ReHUB Scope Checklist & Institutional Verification

**Scope Baseline:** October 2026  
**Applicability:** ReHUB (Rehabilitation Management System) for Kenyan Residential Addiction & Mental-Health Facilities.  
**Version:** 1.0.0-rc1  

## Status Legend
- `[x]` **Implemented:** Fully built, schema migrated, service layer active, validated in API/UI, covered by automated tests.
- `[~]` **Implemented, awaiting institutional acceptance:** Fully built and operable, awaiting facility director / clinical board sign-off or live institutional credentials.
- `[!]` **Production blocker:** Operational, statutory, or infrastructure gate required prior to onboarding live patient data.
- `[ ]` **Not implemented:** Work remaining to be constructed.

---

## 1. Functional Implementation Status

### Phase 1: Foundation, Identity & RBAC Infrastructure
- [x] Modular FastAPI backend and strict TypeScript/React Vite frontend architecture.
- [x] PostgreSQL 18 schema controlled exclusively by versioned Alembic migrations (no startup `create_all`).
- [x] UUIDv4 primary keys, relationship tables, and check constraints across all identity models.
- [x] Argon2 password hashing (`pwdlib[argon2]`) and HTTP-only JWT access tokens (15-min expiry).
- [x] Rotating SHA-256 hashed refresh tokens, server-side revocation, 30-min idle timeout, 7-day absolute lifetime.
- [x] 5-attempt failed-login lockout (15 minutes) with persisted failure counters.
- [x] Mandatory first-login password change for all provisioned and reset accounts.
- [x] Expiring single-use password reset tokens with configurable SMTP delivery abstraction.
- [x] Authoritative server-side `resource.action` RBAC validation on all endpoints.
- [x] Origin validation and anti-CSRF token verification on all state-mutating requests.
- [x] Structural isolation of ICT system administrators from clinical, therapy, and patient health data.
- [x] Append-only `audit_events` with PostgreSQL triggers rejecting `UPDATE`, `DELETE`, and `TRUNCATE`.
- [x] Facility settings persistence (system name, institution name, contact details, logo).
- [x] Responsive layout with desktop sidebar, tablet view, and mobile offcanvas navigation.

### Phase 1.5: Minimum Clinical Safety Guardrails
- [x] Integration of validated Columbia-Suicide Severity Rating Scale (**C-SSRS**) questionnaire and automatic risk scoring.
- [x] Real-time crisis alert system flagging high-risk clinical triggers in unstructured text.
- [x] Clinician crisis alert acknowledgment and notification workflow.
- [x] Persistent, one-click "Get Help Now" emergency directory with direct Kenyan crisis hotlines.

### Phase 2: Client Registry & Admissions Management
- [x] Permanent master `Client` record with human-readable identifier (`ARS-XXXXX`) persisting across multiple admissions.
- [x] Structured referral management with source categorization, urgency triage, and status transitions.
- [x] Pre-admission screening for intoxication, withdrawal, suicide, violence, and medical suitability with mandatory clinician justification.
- [x] Inpatient admission workflow with programme duration, responsible staff, and treatment agreements.
- [x] Hierarchical bed allocation: Facility → Wing → Room → Bed with concurrency collision locks.
- [x] Bed state management (Available, Reserved, Occupied, Cleaning, Maintenance) and audited transfer history.
- [x] Versioned client consent tracking with explicit granted/declined states and withdrawal history.
- [x] Client property, valuables, and prohibited items register with custody sign-off and return tracking.

### Phase 3: Assessments & Rehabilitation
- [x] Configurable multi-substance history catalogue (patterns, frequency, last use, withdrawal, tolerance).
- [x] Standardized psychometric assessment engines (**AUDIT**, **ASSIST**, **CAGE**, **DAST-10**, **PHQ-9**, **GAD-7**).
- [x] Biopsychosocial assessment instrument covering biological, psychological, social, and legal domains.
- [x] Individualized treatment planning with measurable goals, objectives, interventions, and revision history.
- [x] Multidisciplinary team (MDT) case management and assignment workflows.
- [x] Therapy session records (individual, group, family) with strict privilege separation for confidential psychotherapy notes.
- [x] Daily/weekly rehabilitation programme schedules with participant attendance logs.

### Phase 4: Clinical & Nursing Care
- [x] Clinician consultations, physical examinations, problem/diagnosis lists, and medical orders.
- [x] Authoritative vital signs recording with validation and longitudinal trend visualization.
- [x] Nursing observation dashboard, daily care notes, and shift-to-shift handover logs.
- [x] Internal and external laboratory test orders, reference ranges, and abnormal flags.
- [x] Dedicated urine drug screen (Toxicology) panel with multi-substance qualitative/quantitative tracking.
- [x] Non-destructive clinical revisions with historical snapshot preservation.

### Phase 5: Medication & Pharmacy
- [x] Formulations, routes, dosages, and controlled-substance medication catalogue.
- [x] Authorized prescriber workflow with start/stop dates, instructions, and PRN indications.
- [x] Electronic Medication Administration Record (**eMAR**) with ward, client, and round views.
- [x] Enforced administration constraints with mandatory written reasons for omitted or refused doses.
- [x] Pharmacy inventory management: batch tracking, manufacturer expiry alerts, and FIFO dispensing.
- [x] Ward stock transfers, returns, adjustments, and zero-variance physical counts.

### Phase 6: Billing & Payers
- [x] Payer registry with private, corporate, insurance (NHIF/SHA), and family sponsor support.
- [x] Itemized fee catalogues, service price lists, and programme package bundles.
- [x] Server-calculated invoices with tax, discounts, and structured invoice states.
- [x] Payment receipts, invoice allocations, outstanding balances, and debt ageing.
- [x] Credit notes, refunds, write-offs, and adjustments with mandatory justification and audit logging.
- [x] Ledger-linked reconciliation workspace for automatic and manual payment matching.

### Phase 7: Residential Operations & Safeguarding
- [x] Resident movement tracking: planned leave, hospital transfers, AWOL flags, and return verification.
- [x] Approved visitor register, booking, identification, and contraband search logs.
- [x] Incident reporting with severity categorization, investigation notes, and immutable addendum trails.
- [x] Permission-restricted safeguarding register for vulnerable adults and minors.
- [x] Dietary requirements, food allergies, and daily kitchen meal headcounts.

### Phase 8: Discharge & Recovery
- [x] Comprehensive discharge readiness gateway covering medical stability, recovery plan, accommodation, and financial clearance.
- [x] Attributable discharge summaries, medication take-home instructions, and automatic bed release.
- [x] Structured aftercare case management with milestones at 7, 30, 90, 180, and 365 days.
- [x] Relapse logging (substance, trigger, severity) with treatment plan revisions and seamless readmission support.

### Phase 9: Inventory, Staff Roster & Compliance
- [x] General stores items, categories, suppliers, reorder levels, and goods receipt notes.
- [x] Purchase requisition and purchase order approval workflows.
- [x] Staff profiles, professional designations, academic qualifications, and licensing body records.
- [x] Shift rostering, department assignments, and staff leave approvals.
- [x] Statutory compliance registers for **NACADA**, County Health, Fire/Public Health, Pharmacy & Poisons Board, and ODPC.
- [x] Automated compliance expiration alerts (90, 60, 30, 14, and 7 days).

### Phase 10: Reporting, Outcomes & Executive Dashboards
- [x] Role-specific executive, clinical, nursing, rehabilitation, and finance dashboards.
- [x] Live operational metrics: bed occupancy, average length of stay (ALOS), treatment completion rates, and debt ageing.
- [x] Audited CSV and printable structured report exports.

### Phase 11: Redis & Celery Background Execution
- [x] Celery worker and Celery Beat daemon integrated into Docker Compose stack.
- [x] 9 Idempotent scheduled tasks: eMAR rounds, overdue doses, crisis escalation, risk reviews, statutory compliance, aftercare milestones, pharmacy stock, staff licences, overdue invoices.
- [x] Administrative Job Monitoring UI (`/administration/jobs`) with retry, duration, and error visibility.

### Phase 12: M-Pesa Daraja Production Integration
- [x] Safaricom Daraja STK Push (`POST /api/v1/billing/mpesa/stk-push`) and C2B Webhook handler.
- [x] Non-human System Integration Actor for automated transaction attribution.
- [x] Unique transaction reference constraint and DB-level idempotency protection.
- [x] Automatic payment creation, invoice allocation, and balanced General Ledger posting (`Dr 1010`, `Cr 1200`).
- [~] Live Safaricom Daraja Production Credentials (tested & verified via sandbox/simulation engine).

### Phase 13: Clinical Crisis Escalation Engine
- [x] Multi-tier alert lifecycle (`DETECTED` → `NEW` → `ACKNOWLEDGED` → `UNDER_REVIEW` → `RESOLVED`).
- [x] Provider-independent notification engine (`NotificationProvider`) supporting In-App, SMS, and Email.
- [x] Africa's Talking SMS provider adapter with strict privacy masking.
- [x] Secondary clinical keyword scanner with clinical negation heuristics.

### Phase 14: Clinical Configuration Governance
- [x] `ClinicalConfiguration` and `ClinicalApproval` models with versioning.
- [x] Historical snapshot preservation for past client assessment scores.
- [~] Formal Medical Director signature seal (`docs/CLINICAL_CONFIGURATION_APPROVAL.md`).

### Phase 15: Financial Integrity & Double-Entry Accounting
- [x] Pure `Decimal` and PostgreSQL `NUMERIC` representation on all monetary fields.
- [x] Enforced General Ledger balancing (`Total Debit == Total Credit`).
- [x] Non-destructive financial corrections: posted lines immutable; reversals and correcting journals only.
- [x] Fiscal period controls (`OPEN`, `LOCKED`, `CLOSED`) preventing backdated postings.

### Phase 16: Data Protection & ODPC Readiness
- [x] Data Subject Access Requests (DSAR) and rectification workflows.
- [x] Client consent withdrawal without destructive deletion.
- [x] Data breach registry and retention policy review cycles.
- [x] Audited and permission-guarded bulk clinical data exports.

### Phase 17: Backup & Disaster Recovery
- [x] Automated PostgreSQL backup script (`scripts/backup.sh`).
- [x] Isolated test database restoration script (`scripts/restore_test.sh`).
- [x] Formal Disaster Recovery Plan (`docs/DISASTER_RECOVERY.md`) with RPO < 1h, RTO < 30m.

### Phase 18: Observability & Health Endpoints
- [x] Health check probes (`/health/live`, `/health/ready`).
- [x] Request correlation ID (`X-Request-ID`) across Nginx, FastAPI, Celery, and database.
- [x] System version endpoint (`GET /api/v1/system/version`).

### Phase 19: Security Hardening
- [x] Nginx Content Security Policy, Permissions-Policy, and HSTS headers.
- [x] File-upload magic-byte inspection and MIME type validation.
- [x] Endpoint rate limiting on authentication and M-Pesa callbacks.

### Phase 20: Performance Scale & Query Optimization
- [x] B-tree indexing across high-volume identifiers, foreign keys, and audit timestamps.
- [x] Optimized aggregate dashboard queries with zero N+1 ORM patterns.

### Phase 21: UI Accessibility & Clinical Clarity
- [x] Restrained institutional styling using Bootstrap 5 tokens.
- [x] Prominent high-contrast badges for allergies, crisis alerts, and medication warnings.

### Phase 22: Full End-to-End Testing
- [x] 5 Institutional E2E scenarios passing 100% in `backend/app/tests/test_e2e_scenarios.py`:
  - Patient intake to bed release and aftercare.
  - High suicide-risk crisis escalation and resolution.
  - M-Pesa STK push, callback, allocation, and GL posting.
  - Residential contraband incident and closure.
  - Medication prescription, eMAR, and refusal logging.

### Phase 23: Production Docker & Deployment Tooling
- [x] `docker-compose.prod.yml` validated with healthchecks and restart policies.
- [x] Automated release deployment script (`scripts/deploy.py`).

### Phase 24: User Acceptance Testing (UAT) Framework
- [x] Institutional acceptance plan (`docs/UAT_PLAN.md`) across 11 healthcare roles.
- [x] Formal test matrix (`docs/UAT_RESULTS.md`) with 28/28 test cases passed.

### Phase 25: Go-Live Readiness Dashboard
- [x] Administrative readiness view (`/administration/readiness`) tracking 12 institutional gates.

### Phase 26: Unified Human-Readable Reference Codes & Global Quick Search
- [x] Concurrency-safe atomic reference code generator (`app.core.reference_generator.py`) supporting timeless and year-based sequences across record entities (`ARS-`, `MED-`, `STK-`, `STF-`, `ADM-`, `RX-`, `ENC-`, `MO-`, `LAB-`, `INC-`, `CR-`, `INV-`, `RCT-`, `PAY-`, `EXP-`, `JV-`, `SIN-`, `PO-`, `DIS-`, `AFC-`, `VIS-`).
- [x] Alembic migration (`tt5678901234_human_readable_reference_codes.py`) backfilling reference codes with unique indexes and constraints.
- [x] Global unified search API (`GET /api/v1/search/quick`) querying across clients, admissions, prescriptions, medications, invoices, staff, incidents, and inventory with RBAC enforcement.
- [x] Frontend Neumorphic `GlobalQuickSearch` component integrated into institutional topbar (`Ctrl + K` shortcut, instant debounced dropdown, keyboard navigation, categorized badges).

### Phase 26.5: Finance Safety, Accounting Integrity & Control Remediation
- [x] Canonical `Decimal` monetary standard (`app.core.money`) eliminating floating-point rounding errors across billing and GL.
- [x] Full PostgreSQL `NUMERIC` column audit with zero allowed `FLOAT`/`DOUBLE PRECISION` types.
- [x] Decoupled technical administration from financial authority: stripped financial approvals from System Administrator and Super Administrator via forward migration `vv1234567890`.
- [x] Cash reconciliation supervisor gate: zero variance auto-balances (`BALANCED`), non-zero variance requires independent supervisor review (`VARIANCE_REVIEW` -> `POSTED`).
- [x] Enforced immutability of issued invoices (`ISSUED`, `PARTIALLY_PAID`, `PAID`, `OVERDUE`); direct mutation blocked.
- [x] Activated Credit Note workflow with structured reasons, maker-checker authorization (`billing.credit_note.approve`), and atomic GL posting (Dr 4000 / Cr 1200).
- [x] Dual-control Bad Debt Write-Off workflow (`PENDING_APPROVAL` -> `APPROVED`), independent approver gate, senior authorization threshold, and atomic GL posting (Dr 6000 / Cr 1200).
- [x] Pre-issuance pricing discount approval thresholds (> 10% requires supervisory sign-off).
- [x] Strictly atomic billing and GL posting boundaries with zero swallowed exceptions; propagation of `FinancialPostingError`.
- [x] Operational Billing-to-GL Integrity Diagnostic Service (`GET /api/v1/finance/integrity/billing-gl`) verified against non-zero pre-production financial lifecycle dataset (24 records scanned, 0 missing journals, 0 duplicate journals, 1 historical mutation anomaly flagged non-destructively).
- [x] Standardized authoritative Chart of Accounts for cash variances: `6600 Cash shortage expense` (Dr Shortage / Cr Cash 1000) and `4300 Cash overage income` (Dr Cash 1000 / Cr Overage 4300).
- [x] Activated and verified Accounts Payable test suite: `test_supplier_invoice` passing 100% with seeded chart of accounts.
- [x] Frontend Finance Approval Workspace queue and Billing-GL Integrity panel.

### Phase 26.6: End-to-End Client Finance Lifecycle, Financial Documents & Exports
- [x] Pre-admission Financial Assessment workflow (`FAS-YYYY-NNNNN`) tracking payer types, guarantor details, estimated stay, and deposit terms without clinical leakage.
- [x] Commercial Quotations & Cost Estimates (`EST-YYYY-NNNNN`) with line-item categorization, tax/discounts, subtotal/total calculations, and guaranteed zero GL impact.
- [x] Quotation Conversion workflow: Accepted estimates seamlessly convert into formal admission-linked Financial Agreements (`FAG-YYYY-NNNNN v1`).
- [x] Financial Agreement Versioning (`v1`, `v2`): Revisions preserve complete historical lineage, track revision reason and authorization, and enforce maker-checker segregation.
- [x] Programme Package Billing Engine: Inclusions categorized as `INCLUDED`, `LIMITED_QUANTITY`, `DISCOUNTED`, `SEPARATELY_BILLABLE` with automatic consumption tracking and quota-exceeded extra charges.
- [x] Automated Recurring Billing Schedules: Daily/weekly/monthly recurring charges with target-date idempotency, admission-scoping, and auto-cessation upon discharge.
- [x] Cross-Module Billable Activity Integration: Source module deduplication preventing duplicate charges from pharmacy, lab, clinical, or residential extras.
- [x] Split-Payer Financial Architecture: Invoice payer allocations with percentage/amount validation blocking over-allocation (> 100%).
- [x] Sponsor Records (`SPN-YYYY-NNNNN`) & Sponsor Statements consolidating client balances across sponsored admissions with clinical privacy masking.
- [x] Client Financial Account Subledger: Canonical real-time balances for charges, credits, payments, refunds, write-offs, outstanding balance, credit balance, and overdue amounts.
- [x] Structured Payment Plans (`PPL-YYYY-NNNNN`) with installment schedules and status tracking.
- [x] Dual-Control Client Refund Workflow (`RF-YYYY-NNNNN`) with source-based GL posting (`2200 Client Deposits Liability` vs `4000 Programme Revenue`).
- [x] Custodial Resident Pocket Money Subledger (`RFA-YYYY-NNNNN`): Trust account tracking under GL `2200`, strictly non-negative balance checks, and atomic GL journals.
- [x] Discharge Financial Clearance (`CLR-YYYY-NNNNN`): Three independent statuses (Clinical Discharge, Financial Clearance, Administrative Closure) supporting `CLEARED`, `PAYMENT_PLAN`, and `AUTHORIZED_EXCEPTION`.
- [x] Server-Side Financial Document Engine (`FinancialDocumentPdfBuilder`): Generates branded A4/A5 PDFs for all 12 official commercial and accounting documents.
- [x] Structured Spreadsheet Exporters (`FinancialSpreadsheetExporter`): Server-side CSV and XLSX exports for all core reports with mandatory `BillingExportAudit` logging.
- [x] Frontend Client Finance Workspace: Live balance cards, transaction subledger, PDF download triggers, browser `@media print` layout, and spreadsheet export modal.
- [x] 106 backend tests passing (0 skipped, 0 failed); 0 TypeScript errors on frontend production build.

---

## 2. Production Acceptance Gates

| Gate | Status | Requirement & Validation Condition |
|---|:---:|---|
| **Database Migrations** | `[x]` | Single migration head (`ww1234567890`), zero schema drift, verified upgrade/downgrade. |
| **RBAC Security Audit** | `[x]` | Total isolation of IT Admin from clinical and financial approval data; least-privilege role boundaries tested. |
| **Audit Immutability** | `[x]` | PostgreSQL triggers successfully reject `UPDATE`, `DELETE`, and `TRUNCATE` operations on `audit_events`. |
| **Financial Balance Integrity**| `[x]` | General Ledger rejects unbalanced journals; non-destructive reversal entries enforced; strict Decimal arithmetic. |
| **Financial Segregation of Duties** | `[x]` | System Admin cannot approve expenses; cashiers cannot self-approve cash variances; write-offs and credit notes require independent checkers. |
| **Container & Nginx Ingress** | `[x]` | Docker Compose builds cleanly; Nginx rate limiting, security headers, and reverse proxy active. |
| **Clinical Scales Sign-Off** | `[~]` | Medical Director / Clinical Board formal sign-off in `docs/CLINICAL_CONFIGURATION_APPROVAL.md`. |
| **M-Pesa Live Production Keys**| `[~]` | Live Safaricom Daraja Consumer Key, Secret, Shortcode, and Passkey provisioned into `.env`. |
| **Production SMTP Gateway** | `[~]` | Verified delivery of password reset and system alert emails via institutional SMTP/SendGrid. |
| **Disaster Recovery Drill** | `[x]` | Production database backup script executed and verified via clean test database restoration. |
| **ODPC Compliance Review** | `[x]` | Data Protection Officer review of client consent language and data retention schedules under Kenya Data Protection Act. |
| **Institutional Staff UAT** | `[x]` | 28/28 test cases passed across all 11 departments documented in `docs/UAT_RESULTS.md`. |
