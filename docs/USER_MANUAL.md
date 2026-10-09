# ReHUB User Manual

## 1. Introduction
Welcome to **ReHUB** (Rehabilitation Management System). ReHUB is a comprehensive, secure, and production-oriented platform tailored for residential alcohol and substance-use rehabilitation institutions in Kenya. 

This user manual is designed to align with Standard Operating Procedures (SOPs) for rehabilitation centers, ensuring that all staff—Administrators, Clinicians, Nurses, Counsellors, Finance Officers, and Auditors—can seamlessly integrate the system into their daily workflows while maintaining strict data privacy, clinical accuracy, and auditability.

---

## 2. Access Control & Security SOPs
**SOP Alignment:** *Data Privacy, Confidentiality, and Least Privilege Access.*

ReHUB strictly enforces role-based access control (RBAC). Your dashboard and available modules depend on your assigned role.

- **Login & Authentication:** Access the system via the secure login portal using your credentials. Passwords are securely hashed, and session timeouts are enforced for security.
- **Audit Trails:** Every action in ReHUB is recorded. The system uses immutable audit logs (you cannot delete or alter historical records). If an error is made in a clinical entry, a **Revision Workflow** must be used to correct it, preserving the original entry for transparency.
- **Role Separation:** 
  - *IT Administrators* manage user access but cannot view clinical records.
  - *Clinicians & Nurses* handle patient medical data but cannot manipulate billing ledgers.

---

## 3. Admission & Intake SOPs
**SOP Alignment:** *Client Registration, Triage, and Onboarding.*

The admission module handles the transition from a referral or walk-in to a formally admitted client.

1. **Referral & Screening:** 
   - Navigate to **Admissions > New Referral**.
   - Enter basic demographic information and the reason for referral.
2. **Intake Processing:** 
   - Convert a successful screening into an active Admission.
   - Assign the client to a specific residential facility/ward.
   - A unique, permanent Client Record is created across all future admissions to ensure continuity of care.

---

## 4. Clinical Care & Crisis Management SOPs
**SOP Alignment:** *Psychiatric Evaluation, Risk Assessment, and Medical Intervention.*

### 4.1 Initial Assessment
Upon admission, clinicians conduct comprehensive baseline assessments.
- **Assessments Module:** Access standardized assessment tools (e.g., medical history, substance use history).

### 4.2 Crisis Alerts (C-SSRS)
**SOP Alignment:** *Immediate Intervention and Safety Planning.*
- ReHUB includes integrated **Crisis Alerts** utilizing tools like the **Columbia-Suicide Severity Rating Scale (C-SSRS)**.
- If a client scores as Moderate or High/Critical risk, the system generates an immediate alert on the Clinical Dashboard.
- **Action:** Clinicians must navigate to the **Crisis Alerts** widget, review the alert, and formally click **Acknowledge** to document that the intervention protocol has been initiated.

### 4.3 Treatment Planning
- Create individualized Treatment Plans with specific, measurable goals.
- Treatment plans are updated during multidisciplinary team (MDT) meetings.

---

## 5. Counselling & Rehabilitation SOPs
**SOP Alignment:** *Therapeutic Delivery and Progress Tracking.*

Counsellors use this module to track therapeutic interventions.
- **Session Notes:** Record notes for Individual Therapy, Group Therapy, and Family Interventions.
- **Progress Reviews:** Periodically update the client’s progress against their Treatment Plan goals. 
- *Note:* Clinical notes are locked after signing. Addendums must be used for late additions.

---

## 6. Nursing & Medication SOPs
**SOP Alignment:** *Safe Medication Administration and Daily Monitoring.*

- **Vitals Tracking:** Nurses log daily vitals (blood pressure, weight, temperature).
- **Medication Administration:** 
  - Review active prescriptions ordered by clinicians.
  - Log every dose administered. Missed doses must be recorded with an explanatory note.
- **Incident Reporting:** Any incidents (e.g., contraband, altercations, medical emergencies) must be logged immediately via the **Incident Reports** tab.

---

## 7. Finance & Billing SOPs
**SOP Alignment:** *Revenue Management, Transparent Invoicing, and Payment Collection.*

The Finance Service operates independently of clinical modules to maintain financial integrity.
- **Invoicing:** Generate invoices linked to a specific client and admission.
- **Payments:** Record payments received via M-Pesa, bank transfer, or cash.
- **Ledger Integrity:** Like clinical records, financial records cannot be deleted. Any errors require raising a **Credit Note** or **Adjustment**.

---

## 8. Discharge & Aftercare SOPs
**SOP Alignment:** *Safe Exit Planning and Relapse Prevention.*

- **Discharge Planning:** Initiated at least a week before the planned exit. Involves finalizing the discharge summary and aftercare plan.
- **Formal Discharge:** Closes the current admission. The system will flag if there are outstanding invoices that need clearance before physical discharge.
- **Recovery Monitoring:** Schedule automated or manual follow-ups (e.g., 30-day, 90-day check-ins) to monitor sobriety and reintegration.

---

## 9. Reporting & Auditing SOPs
**SOP Alignment:** *Compliance, Quality Assurance, and Facility Management.*

- **Dashboards:** View real-time metrics (e.g., Active Admissions, Outstanding Invoices, Staff on Shift).
- **Report Generation:** Generate periodic reports (Admissions summaries, Financial reconciliation, Clinical outcomes).
- **Compliance:** Auditors can export system-wide audit logs to ensure institutional compliance with healthcare regulations.

---
*End of Manual*
