# Installment Schedules & Payment Plans

## 1. Overview
Payment Plans (`PPL-YYYY-NNNNN`) provide structured installment agreements for clients requiring deferred payment schedules during inpatient care or post-discharge aftercare.

## 2. Schedule Tracking
- Each plan specifies `number_of_installments`, `total_amount`, and generates child installments on `billing_payment_plan_installments`.
- Each installment tracks:
  - `installment_number`
  - `due_date`
  - `amount`
  - `paid_amount`
  - `days_overdue`
  - `status`: `PENDING`, `PARTIALLY_PAID`, `PAID`, `OVERDUE`
- Plan status automatically tracks overall client posture: `DRAFT` → `ACTIVE` → `ON_TRACK` / `OVERDUE` → `COMPLETED` / `DEFAULTED`.

## 3. Maker-Checker Approval
- The finance staff member drafting an installment plan cannot approve it.
- Approval requires independent manager review (`billing.payment_plan.approve`).
