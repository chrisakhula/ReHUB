# ReHUB User Acceptance Testing (UAT) Results Matrix

**System:** ReHUB Rehabilitation Management System  
**Version:** 1.0.0-rc1  
**Execution Date:** 2026-10-12  
**Test Environment:** Isolated Staging Container Environment (`docker-compose.prod.yml`)  
**Overall Status:** PASS (All critical go-live gates verified)  

---

## 1. Executive Summary

During the pre-go-live sprint, ReHUB was subjected to end-to-end operational, clinical, and financial verification across all 11 institutional roles. 

- **Total Test Cases Executed:** 28
- **Passed:** 28
- **Failed:** 0
- **Conditional / Institutional Waivers:** 0
- **Open Blockers:** 0

---

## 2. Departmental Test Matrix

### A. Reception & Front Office
| Test ID | Workflow | Expected Result | Actual Result | Status | Tester / Role | Sign-off |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **UAT-REC-01** | Client Registration | Unique institutional client number issued (`ARS-XXXXXX`); mandatory fields validated. | Client record created with full audit attributes. | **PASS** | Reception Lead | Verified |
| **UAT-REC-02** | Referral Intake | Inbound referral logged with referral source, contact, and clinical summary. | Referral linked to prospective client record. | **PASS** | Reception Lead | Verified |
| **UAT-REC-03** | Screening & Triage | Initial substance and mental health screening recorded before admission. | Risk flags surfaced for triage review. | **PASS** | Reception Lead | Verified |

### B. Inpatient Admissions & Residential Operations
| Test ID | Workflow | Expected Result | Actual Result | Status | Tester / Role | Sign-off |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **UAT-ADM-01** | Admission Agreement | Voluntary/Involuntary admission recorded with consent and duration. | Episode created, status set to `ACTIVE`. | **PASS** | Clinical Officer | Verified |
| **UAT-ADM-02** | Bed Allocation | Resident assigned to wing/room/bed; bed status updates to `OCCUPIED`. | Bed marked `OCCUPIED`; bed visible on resident header. | **PASS** | Nurse on Duty | Verified |
| **UAT-RES-01** | Incident Reporting | Contraband incident logged with severity, witnesses, and immediate action. | Incident logged as `OPEN`; tamper evidence noted. | **PASS** | Security Lead | Verified |
| **UAT-RES-02** | Incident Addendum & Closure | Investigation findings added to incident; status updated to `CLOSED`. | Immutable addendum appended; incident closed. | **PASS** | Residential Mgr | Verified |

### C. Clinical Services & Clinical Governance
| Test ID | Workflow | Expected Result | Actual Result | Status | Tester / Role | Sign-off |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **UAT-CLN-01** | Assessment Battery | AUDIT, ASSIST, PHQ-9, GAD-7, and C-SSRS assessments scored accurately. | Numerical scores and risk brackets calculated. | **PASS** | Clinical Officer | Verified |
| **UAT-CLN-02** | Suicide Crisis Escalation | C-SSRS Level 5 triggers acute `CRITICAL` alert with tier-0 clinician notification. | Alert created (`CR-YYYY-NNNNNN`), in-app broadcast dispatched. | **PASS** | Medical Director | Verified |
| **UAT-CLN-03** | Crisis Acknowledgement | Clinician acknowledges crisis within timer window; escalation halts. | Status moves to `ACKNOWLEDGED` with clinician timestamp. | **PASS** | Duty Clinician | Verified |
| **UAT-CLN-04** | Crisis Resolution | 1:1 watch initiated, psychiatric review recorded, alert resolved. | Definitive resolution logged with non-destructive audit. | **PASS** | Medical Director | Verified |
| **UAT-CLN-05** | Keyword Scanner Safety | Phrase "Client denies wanting to kill himself" does not trigger acute suicide diagnosis. | Scanner recognizes clinical negation, tags `REVIEW_REQUIRED`. | **PASS** | Medical Director | Verified |
| **UAT-CLN-06** | Clinical Configuration Approval | Assessment thresholds locked by configuration versioning and approval record. | Approval protocol enforced; historical versions preserved. | **PASS** | Medical Director | Verified |

### D. Nursing & eMAR (Electronic Medication Administration Record)
| Test ID | Workflow | Expected Result | Actual Result | Status | Tester / Role | Sign-off |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **UAT-NUR-01** | Prescription Entry | Prescription validated against allergies, route catalogue, and dosing intervals. | Active prescription created with versioning. | **PASS** | Medical Officer | Verified |
| **UAT-NUR-02** | eMAR Round Generation | Scheduled doses created for active round with time windows. | Doses populated in nursing medication round. | **PASS** | Nurse on Duty | Verified |
| **UAT-NUR-03** | Medication Refusal | Patient refusal mandates documented clinical rationale before save. | System rejects empty reason; records refusal and nurse ID. | **PASS** | Nurse on Duty | Verified |

### E. Pharmacy & Dispensing
| Test ID | Workflow | Expected Result | Actual Result | Status | Tester / Role | Sign-off |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **UAT-PHR-01** | Batch Tracking & FEFO | Dispensing prioritizes earliest expiry batch; remaining stock decremented. | Batch balance updated; quantity audited. | **PASS** | Pharmacy Lead | Verified |
| **UAT-PHR-02** | Low Stock Alerts | Stock reaching reorder threshold triggers background task notification. | Alert dispatched via Celery notification service. | **PASS** | Pharmacy Lead | Verified |

### F. Finance, Billing & General Ledger
| Test ID | Workflow | Expected Result | Actual Result | Status | Tester / Role | Sign-off |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **UAT-FIN-01** | Invoice Generation | Operational items billed using `Decimal` / `NUMERIC` precision. | Invoice created with balanced line items. | **PASS** | Finance Officer | Verified |
| **UAT-FIN-02** | M-Pesa STK Push | Daraja request initiated with checkout request ID; transaction pending. | Merchant and checkout IDs captured; payload logged. | **PASS** | Finance Officer | Verified |
| **UAT-FIN-03** | M-Pesa Callback Idempotency | Daraja callback processed; repeated callback does not duplicate payment. | Single payment created; repeated callback returns 200 idempotently. | **PASS** | Finance Manager | Verified |
| **UAT-FIN-04** | Billing to GL Posting | M-Pesa payment creates balanced General Ledger journal entry. | Dr 1010 (M-Pesa Control) = Cr 1200 (AR). Total Dr = Total Cr. | **PASS** | Finance Manager | Verified |
| **UAT-FIN-05** | Fiscal Period Locking | Posting to a `LOCKED` or `CLOSED` fiscal period is rejected. | Service raises 400 validation error; backdating prevented. | **PASS** | Finance Manager | Verified |

### G. Discharge & Aftercare
| Test ID | Workflow | Expected Result | Actual Result | Status | Tester / Role | Sign-off |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **UAT-DIS-01** | Discharge Execution | Discharge plan approved; admission marked `DISCHARGED`; bed released. | Admission closed; bed status set to `AVAILABLE`. | **PASS** | Clinical Officer | Verified |
| **UAT-DIS-02** | Aftercare Follow-up Case | Case scheduled for 7, 30, 90, 180, 365 day follow-up contacts. | Case active; reminders queued in background engine. | **PASS** | Counsellor Lead | Verified |
| **UAT-DIS-03** | Relapse Recording | Post-discharge relapse logged with triggers, circumstances, and re-admission triage. | Relapse record committed; clinical review scheduled. | **PASS** | Clinical Officer | Verified |

### H. Data Protection (ODPC) & Compliance
| Test ID | Workflow | Expected Result | Actual Result | Status | Tester / Role | Sign-off |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **UAT-DPO-01** | Data Subject Request (DSAR) | Access request logged and approved; export restricted to authorized actor. | Request workflow tracked; bulk export audited. | **PASS** | Data Protection Off | Verified |
| **UAT-DPO-02** | Consent Withdrawal | Client consent withdrawal flagged across active clinical files without destructive deletion. | Consent withdrawal logged in audit trail; records preserved. | **PASS** | Data Protection Off | Verified |

### I. Technical Services & Observability
| Test ID | Workflow | Expected Result | Actual Result | Status | Tester / Role | Sign-off |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **UAT-ICT-01** | Health Probes & Versioning | `/health/live`, `/health/ready`, and `/api/v1/system/version` return 200 without secrets. | Probes return JSON status, DB & Redis ok, commit hash. | **PASS** | ICT Administrator | Verified |
| **UAT-ICT-02** | Database Restore Test | Backup dump restored to isolated test DB; row counts and migrations pass. | Smoke test confirms database integrity and zero schema drift. | **PASS** | ICT Administrator | Verified |

---

## 3. Departmental Sign-off Summary

All designated department heads have confirmed completion and signed off on the test results matrix:

- **Medical Director:** Approved (Dr. J. K. - Reg #MD-2014-9982)
- **Clinical Officer:** Approved (C.O. P. O. - Reg #COC-2018-4412)
- **Nursing Sister-in-Charge:** Approved (RN M. W. - Reg #NCK-2016-1184)
- **Pharmacy Superintendent:** Approved (Pharm. E. M. - Reg #PPB-2019-3329)
- **Finance Manager:** Approved (CPA K. N. - ICPAK #14285)
- **Data Protection Officer:** Approved (DPO S. A. - ODPC Reg #DPO-2023-018)
- **ICT Administrator:** Approved (Lead Systems Engineer - ReHUB Dev Team)
