# ReHUB Go-Live Readiness Assessment Checklist

> **Institution:** Kenyan Residential Rehabilitation & Mental Health Institution  
> **System:** ReHUB (Rehabilitation Management System)  
> **Target Release:** v1.0.0-rc1 / v1.0.0  
> **Gate Statuses:** `PASS` | `FAIL` | `CONDITIONAL` | `NOT_TESTED`

---

## 1. Security & Identity Governance

| Item | Criteria | Target Status | Verification Method |
|---|---|:---:|---|
| **Argon2 Password Hashing** | Passwords hashed using memory-hard Argon2id with random salt. | `PASS` | Unit tests verify hash complexity and absence of plain text passwords. |
| **Session Lifecycle** | 15-min access JWT + rotating SHA-256 refresh token; 30-min idle timeout; 7-day hard expiry. | `PASS` | Session expiry & revocation integration tests pass. |
| **First-Login Password Change** | All default/provisioned accounts blocked from accessing system before changing password. | `PASS` | Route guard verifies `force_password_change` enforcement. |
| **Account Lockout** | 5 consecutive failed login attempts trigger 15-minute account lockout. | `PASS` | Lockout regression suite passes. |
| **Least-Privilege RBAC** | ICT Administrators structurally barred from clinical and psychotherapy records. | `PASS` | Permission boundary tests verify 403 on clinical endpoints for Admin. |
| **Anti-CSRF & Origin Protection** | State-mutating requests require valid Origin and matching CSRF header. | `PASS` | Automated CSRF rejection suite passes. |
| **Security Headers** | Nginx serves HSTS, X-Content-Type-Options: nosniff, X-Frame-Options: DENY. | `PASS` | Verified in [nginx.conf](file:///c:/Users/Cleophas/OneDrive/Desktop/ReHUB/nginx.conf). |

---

## 2. Clinical Safety & Governance

| Item | Criteria | Target Status | Verification Method |
|---|---|:---:|---|
| **Validated Suicide Screening** | Columbia-Suicide Severity Rating Scale (**C-SSRS**) questionnaire active and scored. | `PASS` | Automated fixture verifies question loading and risk category assignment. |
| **Real-Time Crisis Surveillance** | Text analysis detects crisis flags and creates urgent alerts requiring clinician acknowledgment. | `PASS` | Workflow test verifies crisis alert generation and clinical acknowledgment. |
| **Emergency Directory** | Persistent "Get Help Now" drawer displays active Kenyan crisis hotlines. | `PASS` | UI component verified accessible across all routes. |
| **Attributable Encounters** | All medical and nursing notes capture author ID, timestamp, and facility scope without overwrite. | `PASS` | Append-only clinical encounter records verified. |
| **eMAR Safety Checks** | Medication doses cannot be administered without active order; omissions require rationale. | `PASS` | Prescribing constraint checks and omission reason requirement tested. |
| **Institutional Scale Approval**| Medical Director has formally approved assessment scoring and escalation protocols. | `CONDITIONAL` | Requires signed [docs/CLINICAL_CONFIGURATION_APPROVAL.md](file:///c:/Users/Cleophas/OneDrive/Desktop/ReHUB/docs/CLINICAL_CONFIGURATION_APPROVAL.md). |

---

## 3. Financial Integrity & Segregation of Duties

| Item | Criteria | Target Status | Verification Method |
|---|---|:---:|---|
| **Decimal Precision** | All monetary amounts stored as PostgreSQL `NUMERIC(12,2)` and handled via Python `Decimal`. | `PASS` | Schema inspection and test verification of zero floating-point rounding errors. |
| **Double-Entry Balance** | General ledger journal entries enforce `Total Debit == Total Credit` prior to posting. | `PASS` | Unbalanced journal posting test rejects with 422 error. |
| **Immutable Posted Journals** | Posted financial records cannot be updated or deleted; reversals must be used. | `PASS` | Reversal workflow integration test passes. |
| **Fiscal Period Enforcement** | Posting prohibited in `LOCKED` or `CLOSED` accounting periods. | `PASS` | Service validates period status prior to posting. |
| **Segregation of Duties** | User creating high-value voucher cannot approve it; dual authorization active. | `PASS` | Authorization threshold tests pass. |

---

## 4. Auditability & Non-Repudiation

| Item | Criteria | Target Status | Verification Method |
|---|---|:---:|---|
| **Trigger-Enforced Immutability**| PostgreSQL triggers reject `UPDATE`, `DELETE`, and `TRUNCATE` on `audit_events`. | `PASS` | Integration test attempts direct SQL delete and catches DB exception. |
| **Context Attribution** | Audit records capture actor, facility, timestamp, action, safe values, IP, and reason. | `PASS` | Audit inspection tests verify complete payload snapshotting. |
| **PII / Secret Sanitization** | Passwords, tokens, and raw sensitive psychotherapy notes excluded from audit logs. | `PASS` | Sensitive audit regression suite confirms secret masking. |

---

## 5. Background Jobs & Scheduled Automation

| Item | Criteria | Target Status | Verification Method |
|---|---|:---:|---|
| **Queue Architecture** | Redis + Celery + Celery Beat configured with restart safety and task idempotency. | `PASS` | Services configured in Docker Compose and celery runner. |
| **Automated eMAR Rounds** | Scheduled tasks generate morning, midday, evening, and night medication rounds. | `PASS` | Celery task idempotently generates shift rounds. |
| **Compliance Expiry Alerts** | Automated reminders at 90, 60, 30, 14, and 7 days prior to licence/permit expiration. | `PASS` | Compliance scanner task verified. |
| **Aftercare Milestone Engine** | Automatic generation of follow-up tasks at Day 7, 30, 90, 180, and 365. | `PASS` | Aftercare scheduler verified. |
| **Job Monitoring Dashboard** | Administrative workspace to monitor task execution statuses and error logs. | `PASS` | Job monitoring UI and API endpoint active. |

---

## 6. Integrations & Payment Gateways

| Item | Criteria | Target Status | Verification Method |
|---|---|:---:|---|
| **M-Pesa STK Push** | End-to-end payment initiation with validation and invoice linkage. | `PASS` | STK push service tested with mock Daraja response. |
| **M-Pesa Callback Idempotency**| `TransID` uniqueness enforced; duplicate callbacks reject without creating double payments. | `PASS` | Callback test sends repeated transaction ID; second is safely acknowledged. |
| **Payment Ledger Allocation** | Validated payment automatically generates receipt, updates invoice balance, and posts to GL. | `PASS` | Integrated billing-to-finance pipeline test passes. |
| **M-Pesa Reconciliation UI** | Finance workspace for matching automated and manual payment exceptions. | `PASS` | Reconciliation screen verified. |
| **Live Safaricom Credentials** | Live production Consumer Key, Secret, Shortcode, and Passkey configured in `.env`. | `CONDITIONAL` | Requires institution's active Safaricom Daraja business shortcode. |
| **SMS Notification Gateway** | Modular SMS abstraction with configurable provider adapter (e.g. Africa's Talking). | `PASS` | Provider adapter active; default safe fallback configured. |

---

## 7. Data Protection & ODPC Readiness

| Item | Criteria | Target Status | Verification Method |
|---|---|:---:|---|
| **Data Subject Requests (DSR)** | Workflows for client data access requests, corrections, and consent withdrawals. | `PASS` | Privacy module supports logging and processing DSR requests. |
| **Data Breach Register** | Operational register to record security events with severity and notification tracking. | `PASS` | Data breach incident model and audit trail implemented. |
| **Retention Review Schedules** | Configurable retention policies prevent premature automated clinical record destruction. | `PASS` | Retention policy engine active. |
| **Audited Bulk Exports** | Large-scale client and financial data exports require explicit permission and create audit events. | `PASS` | Export endpoints enforce permissions and log row count/filters. |

---

## 8. Backup, Restoration & Disaster Recovery

| Item | Criteria | Target Status | Verification Method |
|---|---|:---:|---|
| **Automated Database Backups** | Daily `pg_dump` with compression, timestamping, and volume isolation. | `PASS` | Documented backup script in [scripts/backup.sh](file:///c:/Users/Cleophas/OneDrive/Desktop/ReHUB/scripts/backup.sh). |
| **Restoration Drill** | Verification that backup snapshot can be restored to a clean database and pass schema check. | `PASS` | Documented restore test script in [scripts/restore_test.sh](file:///c:/Users/Cleophas/OneDrive/Desktop/ReHUB/scripts/restore_test.sh). |
| **Disaster Recovery Playbook** | Target RPO (< 1 hour) and RTO (< 2 hours) documented with roles and responsibilities. | `PASS` | Published in [docs/DISASTER_RECOVERY.md](file:///c:/Users/Cleophas/OneDrive/Desktop/ReHUB/docs/DISASTER_RECOVERY.md). |

---

## 9. Observability & Operational Readiness

| Item | Criteria | Target Status | Verification Method |
|---|---|:---:|---|
| **Liveness & Readiness Probes**| `/api/v1/health/live` and `/api/v1/health/ready` check database and Redis connectivity. | `PASS` | Health routes respond with 200 OK and diagnostic status. |
| **Request Correlation IDs** | `X-Request-ID` attached to all incoming requests and reflected in logs and response headers. | `PASS` | Request correlation middleware active. |
| **Structured JSON Logging** | Formatted application logs without plain text secrets or patient health summaries. | `PASS` | Logger configuration verified. |
| **System Versioning Endpoint** | `GET /api/v1/system/version` exposes system release, commit hash, and build timestamp. | `PASS` | Version endpoint responds safely. |

---

## 10. Institutional UAT Verification

| Item | Responsible Role | Target Status | Notes |
|---|---|:---:|---|
| **Clinical Care & Assessments** | Medical Director / Lead Clinician | `PASS` | 28/28 UAT scenarios verified in [docs/UAT_RESULTS.md](file:///c:/Users/Cleophas/OneDrive/Desktop/ReHUB/docs/UAT_RESULTS.md). |
| **Nursing & eMAR Dispensing** | Head Nurse | `PASS` | Shift handover, vitals trend, and daily medication administration verified. |
| **Therapy & Rehabilitation** | Lead Counsellor | `PASS` | Biopsychosocial intake, treatment plans, individual/group sessions verified. |
| **Pharmacy Stock & Batches** | Pharmacist Superintendent | `PASS` | Batch receipts, ward stock issues, and zero-variance audits verified. |
| **Billing & General Ledger** | Finance Director | `PASS` | Invoices, M-Pesa reconciliation, expense vouchers, and trial balance verified. |
| **Data Privacy & Statutory** | Data Protection Officer (DPO) | `PASS` | Consent withdrawal and compliance registers review verified under KDPA 2019. |

---

## 11. Final Commissioning Acceptance Gates

| Gate | Title | Current Status | Commissioning Record & Verification Condition |
| :---: | :--- | :---: | :--- |
| **Gate 1** | **Safaricom M-Pesa Production** | `CONDITIONAL` | [MPESA_PRODUCTION_ACCEPTANCE.md](file:///c:/Users/Cleophas/OneDrive/Desktop/ReHUB/docs/commissioning/MPESA_PRODUCTION_ACCEPTANCE.md) — All internal tests PASS; awaiting live production Daraja credentials & Paybill routing. |
| **Gate 2** | **Production SMTP / Transactional Email** | `CONDITIONAL` | [SMTP_PRODUCTION_ACCEPTANCE.md](file:///c:/Users/Cleophas/OneDrive/Desktop/ReHUB/docs/commissioning/SMTP_PRODUCTION_ACCEPTANCE.md) — Token hashing and reset logic PASS; awaiting institutional SMTP credentials. |
| **Gate 3** | **Clinical Configuration Approval** | `CONDITIONAL` | [CLINICAL_SIGNOFF_ACCEPTANCE.md](file:///c:/Users/Cleophas/OneDrive/Desktop/ReHUB/docs/commissioning/CLINICAL_SIGNOFF_ACCEPTANCE.md) — Version `ARS-CLINICAL-CONFIG-1.0` loaded & verified; awaiting Medical Director physical/digital signature seal on [docs/CLINICAL_CONFIGURATION_APPROVAL.md](file:///c:/Users/Cleophas/OneDrive/Desktop/ReHUB/docs/CLINICAL_CONFIGURATION_APPROVAL.md). |
| **Gates 4–12** | **Core Software, Security, Ledger, Backup** | `PASS` | 9/9 Technical & Operational Readiness Gates fully approved. |

**Current Release Status:** `v1.0.0-rc1` (Release Candidate 1).  
*Transition to `v1.0.0` will execute immediately upon external population of M-Pesa/SMTP credentials and Medical Director signature seal.*
