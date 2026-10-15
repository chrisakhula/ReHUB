# ReHUB User Acceptance Testing (UAT) Plan

**System:** ReHUB Rehabilitation Management System  
**Version:** 1.0.0-rc1  
**Jurisdiction:** Republic of Kenya (MOH, NACADA, ODPC compliant)  
**Document Status:** Formal Institutional Protocol  

---

## 1. Executive Summary & Objectives

The purpose of this User Acceptance Testing (UAT) Plan is to establish a rigorous, role-delimited framework for validating the clinical safety, financial integrity, data protection compliance, and operational reliability of ReHUB prior to onboarding real patients.

UAT validates that ReHUB satisfies all institutional workflows across residential addiction treatment and mental health rehabilitation as operated in Kenya.

---

## 2. Participating Institutional Roles & Responsibilities

| Role | Department | Primary Acceptance Scope |
| :--- | :--- | :--- |
| **Medical Director** | Medical / Clinical Governance | Clinical configuration approval (AUDIT/ASSIST/PHQ-9/GAD-7/C-SSRS), crisis escalation policy, observation schedules. |
| **Clinical Officer** | Clinical Services | Client assessments, psychiatric reviews, treatment plans, clinical notes, discharge clearances. |
| **Nurse** | Inpatient Nursing | Bed allocation, vital signs, medication administration rounds (eMAR), refusal logging, allergy warnings. |
| **Counsellor** | Psychology & Rehabilitation | Counselling notes, 12-step milestone tracking, therapy group sessions, family support meetings. |
| **Pharmacy Officer** | Pharmacy & Dispensing | Drug catalogue, batch management, FEFO dispensing against active prescriptions, stock alerts. |
| **Finance Manager** | Finance & Accounting | Billing, M-Pesa STK push and C2B payments, general ledger double-entry balancing, fiscal periods. |
| **Receptionist** | Front Office & Intake | Client registration, referrals, initial screening, admission onboarding, identity checks. |
| **Stores / Inventory** | Residential Operations | Facility assets, contraband control, inventory intake and reorder alerts. |
| **Management / CEO** | Executive Governance | Institutional reporting, occupancy overview, safeguarding incident reviews, fiscal period approvals. |
| **ICT Administrator** | Technical Services | Role-based access control (RBAC), background jobs monitoring, backups, disaster recovery, system versioning. |
| **Data Protection Officer (DPO)** | Compliance & ODPC | Data subject access requests (DSAR), consent withdrawal, breach register, data export authorization, retention. |

---

## 3. Defect Classification & Acceptance Criteria

### Defect Severity Definitions:
- **Severity 1 (Blocker):** Data corruption, General Ledger out-of-balance, unhandled exception preventing core patient care or medication administration, failure of crisis alert notification, or unauthorized cross-facility access. *Production blocker: Must be resolved prior to Go-Live.*
- **Severity 2 (Critical):** Major workflow failure with no immediate clinical or financial workaround (e.g. inability to process M-Pesa callback, failure to release bed upon discharge). *Must be resolved or provided with institutional workaround.*
- **Severity 3 (Major):** Workflow impairment with viable manual workaround (e.g. filtering issue on non-critical reporting view).
- **Severity 4 (Minor):** Cosmetic alignment, minor typography or non-blocking label phrasing.

### Go-Live Acceptance Gate:
1. **Zero Severity 1 (Blocker)** defects open.
2. **Zero Severity 2 (Critical)** defects open without signed Medical Director / Finance Manager waiver.
3. **100% Pass** on Double-Entry Accounting Balancing (`Debit == Credit`).
4. **100% Pass** on M-Pesa Idempotent Reconciliation.
5. **100% Pass** on eMAR Administration & Refusal Audit Trail.
6. Formal sign-off by all 11 Departmental Leads.

---

## 4. Test Environment & Data Governance

1. **Environment:** Staging / Isolated UAT Instance (`docker-compose.prod.yml` running on dedicated institutional server).
2. **Data Policy:** Purely synthetic patient personas adhering strictly to the Kenya Data Protection Act 2019. No actual patient PII or real national IDs permitted during testing.
3. **Audit Immutability:** UAT activities must generate verifiable entries in `audit_events` and `finance_journal_entries`. Destructive updates to clinical or financial records are strictly prohibited.

---

## 5. Departmental Test Execution Schedule

| Stage | Department / Modules | Duration | Exit Criteria |
| :--- | :--- | :--- | :--- |
| **Stage 1** | Reception & Intake (Screening, Admission, Beds) | Day 1-2 | Intake to Bed Assignment verified |
| **Stage 2** | Clinical Care & Nursing (Assessments, eMAR, Crisis) | Day 3-5 | Prescriptions, eMAR & Crisis Escalations verified |
| **Stage 3** | Pharmacy & Inventory (Dispensing, Batches) | Day 6 | FEFO Dispensing & Stock alerts verified |
| **Stage 4** | Finance & Billing (M-Pesa, GL, Fiscal Periods) | Day 7-8 | Zero GL drift, M-Pesa reconciliation verified |
| **Stage 5** | Discharge & Aftercare (Discharge, Follow-up, Relapse) | Day 9 | Case closure & aftercare intervals verified |
| **Stage 6** | Governance, DPO & ICT (Backups, ODPC, Celery) | Day 10 | Restore test, DSAR flow, worker monitoring verified |

---

## 6. Formal Sign-Off Authorization

Testing outcomes and sign-off records are formally tracked in [docs/UAT_RESULTS.md](file:///c:/Users/Cleophas/OneDrive/Desktop/ReHUB/docs/UAT_RESULTS.md).
