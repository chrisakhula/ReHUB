# ReHUB Changelog

All notable changes to the ReHUB Rehabilitation Management System are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0-rc3] - 2026-10-16

### Milestone: Phase 26.6 — End-to-End Client Finance Lifecycle, Financial Documents & Exports

This release completes the rehabilitation-specific client financial journey on top of the hardened Phase 26.5 General Ledger core, introducing commercial workflows, versioned agreements, package consumption tracking, split-payer billing, resident pocket money liability subledger, branded server-side PDF generation, and structured spreadsheet exports:

### Added & Implemented
- **Pre-Admission Financial Assessment (`FAS-YYYY-NNNNN`):** Structured commercial assessment capturing primary/secondary payers, sponsors, estimated stay, and deposit rules without clinical leakage.
- **Quotations / Cost Estimates (`EST-YYYY-NNNNN`):** Commercial cost estimates with itemized categories, subtotals, totals, and zero General Ledger impact.
- **Quotation-to-Agreement Conversion:** Seamlessly converts accepted estimates into admission-linked Financial Agreements (`FAG-YYYY-NNNNN v1`).
- **Financial Agreement Versioning (`v1`, `v2`):** Non-destructive revision tracking preserving historical admission contracts, revision reasons, and maker-checker segregation.
- **Programme Package Consumption Engine:** Multi-tier package inclusions (`INCLUDED`, `LIMITED_QUANTITY`, `DISCOUNTED`, `SEPARATELY_BILLABLE`) tracking allowed, used, remaining quotas and generating extra charges upon quota exhaustion.
- **Automated Recurring Billing:** Daily, weekly, and monthly recurring billing engine with date-level idempotency, admission-scoping, and auto-cessation upon client discharge.
- **Split-Payer Financial Architecture:** `InvoicePayerAllocation` supporting split responsibility (percentage or amount) with strict validation preventing over-allocation (> 100%).
- **Sponsor Ledger & Consolidated Statements (`SPN-YYYY-NNNNN`):** Consolidated financial statements for sponsoring foundations/churches/employers with zero clinical narrative leakage.
- **Client Financial Account Subledger:** Real-time canonical calculation of charges, credits, payments, refunds, write-offs, outstanding balance, credit balance, and overdue amounts.
- **Structured Payment Plans (`PPL-YYYY-NNNNN`):** Multi-installment repayment schedules with due dates, payment status tracking, and maker-checker approval.
- **Dual-Control Client Refunds (`RF-YYYY-NNNNN`):** Segregation-of-duties protected refund requests with dynamic GL source routing (Dr `2200 Client Deposits Liability` or Dr `4000 Programme Revenue` / Cr Cash/Bank/M-Pesa).
- **Resident Funds Pocket Money Subledger (`RFA-YYYY-NNNNN`):** Custodial trust accounts under GL `2200`, strictly non-negative balance enforcement, and atomic GL journals.
- **Discharge Financial Clearance (`CLR-YYYY-NNNNN`):** Independent three-tier separation of Clinical Discharge, Financial Clearance (`CLEARED`, `PAYMENT_PLAN`, `AUTHORIZED_EXCEPTION`, `REFUND_DUE`), and Administrative Closure.
- **Server-Side Financial Document Engine:** Branded A4/A5 PDF generation (`FinancialDocumentPdfBuilder`) for Estimates, Agreements, Invoices, Receipts, Statements, Clearances, and Resident Funds.
- **Structured Report Spreadsheet Exporters:** Reusable CSV & XLSX exports with mandatory `BillingExportAudit` audit logging.
- **Frontend Client Finance Workspace & Print Engine:** Neumorphic real-time balance metrics, statement subledger, PDF downloads, `@media print` layout, and expanded Billing Workspace resources.
- **Database & Test Suite Verification:** Alembic single head `ww1234567890`; 106 automated backend tests passing (0 skipped, 0 failed); 0 TypeScript errors on frontend production build.

---

## [1.0.0-rc2] - 2026-10-16

### Milestone: Phase 26.5 — Finance Safety, Accounting Integrity & Control Remediation

This release remediates 7 critical financial control and accounting integrity defects identified during the comprehensive read-only finance audit:

### Changed & Hardened
- **Monetary Arithmetic (P0-1):**
  - Replaced all floating-point arithmetic with canonical `Decimal` quantization (`app.core.money`, `MONEY_QUANTUM = Decimal("0.01")`, `ROUND_HALF_UP`).
  - Audited all financial database columns; verified PostgreSQL `NUMERIC` types across invoices, line items, payments, allocations, vouchers, journal lines, and write-offs.
- **Segregation of Duties & RBAC (P0-2):**
  - Revoked all financial approval and configuration permissions (`finance.approve`, `finance.close_period`, `finance.reopen_period`, `finance.reconcile`, `billing.credit_note.approve`) from `System Administrator` and `Super Administrator` via forward migration `vv1234567890`.
  - Enforced explicit technical administrator lockout in backend expense approvals.
  - Implemented configurable senior financial approval threshold (`finance_expense_senior_approval_threshold = 50000.00`).
- **Cash Reconciliation Supervisory Gate (P0-3):**
  - Converted cash reconciliation into a multi-stage gated workflow. Zero-variance counts transition to `BALANCED`; non-zero variances transition to `VARIANCE_REVIEW` and require independent supervisor review before General Ledger posting.
  - Enforced strict maker-checker validation preventing cashiers from approving their own shortages or overages.
  - Standardized authoritative Chart of Accounts for cash variances: `6600 Cash shortage expense` (Dr Shortage / Cr Cash 1000) and `4300 Cash overage income` (Dr Cash 1000 / Cr Overage 4300).
- **Invoice Immutability & Credit Notes (P0-4):**
  - Enforced financial immutability for issued invoices (`ISSUED`, `PARTIALLY_PAID`, `PAID`, `OVERDUE`); direct mutation of totals, tax, discounts, or line items is strictly prohibited.
  - Preserved original issued `total_amount` during Credit Note lifecycle, updating net remaining balance dynamically (`total_amount - credits - allocations`).
  - Activated the Credit Note workflow with structured reasons (`BILLING_ERROR`, `DUPLICATE_CHARGE`, `SERVICE_NOT_DELIVERED`, `APPROVED_DISCOUNT`, `EARLY_DISCHARGE_ADJUSTMENT`, `OTHER`), maker-checker authorization (`billing.credit_note.approve`), and atomic GL posting (`Dr 4000 Patient Service Revenue / Cr 1200 Accounts Receivable`).
- **Atomic Billing & GL Posting (P0-5):**
  - Removed all silent exception swallowing (`except Exception: pass`, unhandled `logger.warning`) across billing and ledger posting pathways.
  - Enforced single database transaction boundaries for invoice issuance, payment allocations, credit notes, write-offs, and cash variances.
  - Introduced `FinancialPostingError` (HTTP 422) ensuring transactions roll back cleanly without partial financial state.
- **Bad Debt Write-Off Maker-Checker (P0-6):**
  - Replaced single-step write-offs with a two-stage maker-checker request workflow (`PENDING_APPROVAL` -> `APPROVED`).
  - Prohibited requesters from self-approving write-offs; enforced senior management authorization for amounts > KES 50,000.00; and made GL posting atomic (`Dr 6000 Bad Debt Expense / Cr 1200 Accounts Receivable`).
- **Discounts & Billing Adjustment Controls (P0-7):**
  - Separated pre-issuance pricing discounts from post-issuance balance reductions (requiring credit notes).
  - Enforced supervisory approval for pre-issuance discounts exceeding 10%.
- **Billing-to-GL Integrity Diagnostic Service:**
  - Added `app.services.integrity.BillingGlIntegrityService` and diagnostic endpoint `GET /api/v1/finance/integrity/billing-gl` (`finance.audit`) verifying invoice totals, payment allocations, credit notes, and write-offs against General Ledger journals with zero silent auto-corrections.
  - Verified scanner against a non-zero pre-production financial lifecycle dataset (24 records checked, 23 matched, 0 missing, 0 duplicates, 1 historical mutation anomaly flagged non-destructively).
- **Accounts Payable Verification:**
  - Activated and resolved supplier invoice test suite (`test_supplier_invoice` passing 100%).
- **Frontend Operational Workspaces:**
  - Integrated `FinanceApprovalWorkspace` (unified queue for expenses, cash variances, credit notes, and write-offs) and `FinanceIntegrityPanel` into the finance portal.

---

## [1.0.0-rc1] - 2026-10-12

### Milestone: Production Hardening, Automation, Integrations & Institutional Go-Live Readiness

This release hardens ReHUB from a functional multi-phase prototype into a defensible, production-grade institutional EHR and ERP platform for residential addiction and mental health institutions in Kenya.

### Added
- **Redis & Celery Background Execution (Phase 11 & 12):**
  - Integrated Celery worker daemon and Celery Beat periodic scheduler with Redis broker.
  - Added restart-safe, idempotent, facility-scoped scheduled tasks:
    - `generate_emar_rounds`: Periodic eMAR administration round generation.
    - `detect_overdue_medications`: Overdue dose alerts with missing reason tracking.
    - `escalate_critical_alerts`: Automated crisis alert tier escalation.
    - `detect_overdue_risk_reviews`: Clinical risk assessment review prompts.
    - `check_compliance_expiry`: Multi-stage licence expiry warnings (90d, 60d, 30d, 14d, 7d).
    - `process_aftercare_milestones`: Structured aftercare follow-up scheduling (7d, 30d, 90d, 180d, 365d).
    - `check_pharmacy_batches`: FEFO batch expiration and reorder threshold alerts.
    - `check_staff_licence_expiry`: Clinical staff professional council credential expiry warnings.
    - `check_overdue_invoices`: Fiscal invoice aging and payment reconciliation scans.
  - Dedicated administrative Job Monitoring UI (`/administration/jobs`) displaying execution status, duration, retry counts, and sanitized error traces.

- **M-Pesa Daraja Production Integration (Phase 12):**
  - Production-grade Safaricom Daraja STK Push (`POST /api/v1/billing/mpesa/stk-push`) and C2B Webhook handler.
  - Non-human System Integration Actor (`System Integration User`) for automated transaction attribution.
  - Enforced receipt number uniqueness constraints and PostgreSQL transaction locking to guarantee callback idempotency.
  - Automatic invoice payment creation, allocation, and balanced General Ledger journal entry posting (`Dr M-Pesa Control 1010`, `Cr Accounts Receivable 1200`).
  - Finance Reconciliation Workspace with filtering across `AUTO_RECONCILED`, `MANUAL_REVIEW`, `UNMATCHED`, and manual allocation workflows.

- **Clinical Crisis Escalation & Notification Abstraction (Phase 13 & 14):**
  - Multi-tier clinical crisis escalation lifecycle (`DETECTED` -> `NEW` -> `ACKNOWLEDGED` -> `UNDER_REVIEW` -> `RESOLVED`).
  - Provider-agnostic notification engine (`NotificationProvider`) supporting In-App, Email, and SMS (Africa's Talking adapter).
  - Strict SMS privacy masking (zero clinical diagnostics, suicidal ideation, or psychotherapy notes in transit).
  - Safe secondary clinical keyword scanner with clinical negation heuristics (e.g. "Client denies wanting to harm himself" correctly tagged as `REVIEW_REQUIRED`).
  - Institutional Clinical Configuration Governance (`ClinicalConfiguration`, `ClinicalApproval`) locking clinical assessment cutoffs and suicide escalation thresholds.

- **Financial Integrity & Double-Entry Accounting (Phase 15):**
  - Enforced exact `Decimal` and PostgreSQL `NUMERIC` representation across all monetary columns.
  - Enforced strict General Ledger balancing (`Total Debit == Total Credit`) at both service and model validation levels.
  - Non-destructive financial correction rules: immutable posted journal lines with formal reversal and correcting journal workflows.
  - Fiscal Period Controls (`OPEN`, `LOCKED`, `CLOSED`) preventing backdated postings into closed accounting periods.

- **Data Protection & ODPC Readiness (Phase 16):**
  - Kenya Data Protection Act (2019) compliance module: Data Subject Access Requests (DSAR), rectification, consent withdrawal, and data breach registry.
  - Configurable data retention policies with review workflows (`ACTIVE`, `REVIEW_DUE`, `LEGAL_HOLD`, `ARCHIVED`, `ELIGIBLE_FOR_DISPOSAL`).
  - Audited and permission-guarded bulk clinical data exports.

- **Backup, Disaster Recovery & Observability (Phase 17 & 18):**
  - Automated PostgreSQL snapshot script (`scripts/backup.sh`) and isolated verification tool (`scripts/restore_test.sh`).
  - Formal Disaster Recovery Runbook (`docs/DISASTER_RECOVERY.md`) defining RPO (< 1 hour) and RTO (< 30 minutes).
  - Production health probes (`/health/live`, `/health/ready`) and system version endpoint (`/api/v1/system/version`).
  - `X-Request-ID` correlation middleware linking requests across Nginx, FastAPI, Celery, and PostgreSQL.

- **Security & Performance Scale (Phase 19 & 20):**
  - Hardened Nginx configuration with Content Security Policy (CSP), Strict-Transport-Security (HSTS), and rate limiting.
  - Comprehensive PostgreSQL btree indexing on high-cardinality clinical, financial, and audit keys.
  - File-upload hardening with MIME type verification and magic-byte inspection.

- **Institutional UAT Framework & Go-Live Readiness (Phase 24 & 25):**
  - Multi-department User Acceptance Testing Protocol (`docs/UAT_PLAN.md`) and verified test matrix (`docs/UAT_RESULTS.md`).
  - Administration-only Go-Live Readiness Assessment dashboard (`/administration/readiness`) tracking 12 formal operational gates.
  - Automated deployment runner (`scripts/deploy.py`).

- **Unified Human-Readable Reference Codes & Global Quick Search (Phase 26):**
  - Concurrency-safe atomic reference code generator (`app.core.reference_generator.py`) supporting timeless and year-based sequences across record entities (`ARS-`, `MED-`, `STK-`, `STF-`, `ADM-`, `RX-`, `ENC-`, `MO-`, `LAB-`, `INC-`, `CR-`, `INV-`, `RCT-`, `PAY-`, `EXP-`, `JV-`, `SIN-`, `PO-`, `DIS-`, `AFC-`, `VIS-`).
  - Alembic migration (`tt5678901234_human_readable_reference_codes.py`) backfilling reference codes with unique indexes and constraints.
  - Global unified search API (`GET /api/v1/search/quick`) querying across clients, admissions, prescriptions, medications, invoices, staff, incidents, and inventory with RBAC enforcement.
  - Frontend Neumorphic `GlobalQuickSearch` component integrated into institutional topbar (`Ctrl + K` shortcut, instant debounced dropdown, keyboard navigation, categorized badges).

### Changed
- Refactored `DischargeService` to enforce clean dictionary extraction on plan creation.
- Preserved restrained, accessible institutional healthcare UI styling (Bootstrap 5) with high-visibility allergy, crisis, and medication warning badges.
- Upgraded Alembic migration revisions up to `tt5678901234`.
