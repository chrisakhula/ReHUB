# Programme Package Billing & Consumption Tracking

## 1. Concept
ReHUB rehabilitation programmes (e.g. 30-Day, 60-Day, 90-Day Residential Programmes, Detoxification, Aftercare) are packaged with structured service inclusions to prevent double-charging clients for bundled care.

## 2. Service Inclusion Classifications
Under `billing_package_service_inclusions`, services are mapped to packages under four rules:
1. `INCLUDED`: Unlimited bundled service within the package duration (e.g. routine nursing, meals, accommodation).
2. `LIMITED_QUANTITY`: Capped quota of sessions (e.g. 12 individual psychotherapy sessions, 4 family therapy sessions, 2 psychiatric reviews).
3. `DISCOUNTED`: Provided at an agreed percentage discount from standard price list.
4. `SEPARATELY_BILLABLE`: External hospital referrals, specialized dental procedures, non-formulary medications.

## 3. Package Consumption Engine
- When a client is admitted, package inclusions initialize a `billing_package_consumption` tracker for that admission.
- As clinical sessions or nursing procedures are recorded:
  - If `quantity_remaining >= requested_quantity`: Covered under package (`extra_billed = 0`).
  - If quota is exhausted: Automatically transitions to `QUOTA_EXCEEDED`, and extra units generate billable items on the client's admission invoice.
  - Included items cannot be billed twice.

## 4. Recurring Billing
- Configured via `billing_recurring_schedules` for recurring periodic supplements (e.g. daily high-dependency observation care, weekly counseling retainers).
- **Idempotency Guarantee**: Date-level unique fingerprinting (`source_module="RECURRING"`, `source_id="{schedule_id}:{target_date}"`) guarantees that re-running recurring billing cycles never produces duplicate charges.
- Automatically ceases billing once an admission enters `DISCHARGED` or `CLOSED` state.
