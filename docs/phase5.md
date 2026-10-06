# Phase 5: Medication, eMAR and pharmacy

## Architecture and entities

Medication APIs delegate to `MedicationService` and `MedicationRepository`; they share the facility-scoped client/admission contract and request transactions. ORM models are in `backend/app/models/medication.py`, authoritative Pydantic schemas in `schemas/medication.py`, and routes in `api/v1/medication/routes.py`. The React workspaces are `modules/medication/MedicationPage.tsx` and `modules/pharmacy/PharmacyPage.tsx`, using the typed reusable care form/table components.

| Entity | Purpose |
| --- | --- |
| MedicationRoute | Configurable route reference catalogue |
| Medication | Generic/brand name, strength, formulation, unit, active state and reorder level |
| Prescription | Client/admission link, medication snapshot, dose/route/frequency, dates, PRN instructions, responsible prescriber, state and version |
| PrescriptionRevision | Immutable version snapshot and reason |
| MedicationDose | Version-specific scheduled dose and due/recorded/cancelled state |
| MedicationAdministration | Prescribed/actual dose, route, scheduled/actual time, staff, outcome and reason |
| AdministrationAddendum | Attributable correction text without overwriting the original administration |
| PharmacySupplier | Supplier name, contact details and active state |
| DrugBatch | Medication/supplier, batch number, expiry, quantity, unit and receipt reference |
| WardStock | Batch stock allocated to a named ward location |
| PharmacyMovement | Immutable receipt/issue/dispensing/return/adjustment/damage/expiry ledger |
| PharmacyStockCount | Expected and counted quantities, variance, reason and attribution, including zero variance |

UUID foreign keys, indexed facility/admission/batch links, unique scheduled slots, prescription versions and nonnegative stock/dose constraints support integrity. Batch and prescription row locks serialize concurrent mutations. No destructive record endpoints exist. Database triggers protect administration, prescription history, stock-movement and count records from mutation/deletion.

## Migrations and references

- `6b7fa2fc9da8`: medication/prescription/eMAR/pharmacy entities.
- `45ec2a926701`: non-destructive care storage and immutable history protections.
- `e20658b750bf`: stock count register.
- `311f41459de0`: additional register protections.

`seed_care.py` supplies route references and explicit clinical/nursing/pharmacy permissions. It does not seed prescriptions or real client data. Default ICT roles receive no prescribing, administering or clinical-reading privileges.

## API and permissions

All paths below use `/api/v1`.

| API | Purpose / permission |
| --- | --- |
| `/medication/catalogue` | Paginated reading with `medication.view`; POST/PUT catalogue with `pharmacy.manage` |
| `/medication/routes` | Route reading; configured route creation with `pharmacy.manage` |
| `/medication/prescriptions` | Paginated reading with `medication.view`; create/revise with `medication.prescribe` |
| `/medication/prescriptions/{id}/status` | Prescriber-controlled activation, suspension, discontinuation or completion |
| `/medication/prescriptions/{id}/history` | Permission-protected immutable version history |
| `/medication/schedule` | Generate up to seven days of scheduled doses with `medication.administer` |
| `/medication/due` | Due records by admission, wing/ward, date and scheduled round; `medication.view` |
| `/medication/administrations` | Read with `medication.view`; record an outcome with `medication.administer` |
| `/medication/administrations/{id}/addenda` | Read/add correction records without altering the original |
| `/pharmacy/suppliers`, `/pharmacy/batches` | Read with `pharmacy.view`; create suppliers/receive batches with `pharmacy.manage` |
| `/pharmacy/movements` | Immutable movement history; dispensing and ward transfers require `pharmacy.dispense`, adjustments additionally require `pharmacy.manage` |
| `/pharmacy/counts` | Count history; reconciliation with `pharmacy.manage` |
| `/pharmacy/ward-stock`, `/pharmacy/alerts` | Ward balances, expiry and low-stock alerts with `pharmacy.view` |

## Behavior and limits

Prescriptions begin in Draft. Each revision retains a snapshot, cancels outstanding old-version doses, returns the revised order to Draft and requires prescriber activation. Expected-version checks reject stale changes. Medication and route must be active, units must match the catalogue and prescription dates must be valid for the admission. Recorded allergy-name matches require a prescriber review reason.

Rounds use entered daily times in East Africa Time or a fixed hourly interval. PRN orders create no scheduled doses; an optional entered minimum interval is enforced. Repeated schedule generation is idempotent, and previously recorded slots are not silently regenerated when an order changes version.

Administration records preserve the prescription version. Refused, omitted and other non-given outcomes require a reason and no positive actual dose. A changed actual dose requires explanation. Given/PRN records require a positive dose. Duplicate scheduled outcomes and administration under inactive/expired orders are rejected.

Pharmacy receipts create an initial ledger movement. Dispensing checks the batch against the active prescription and rejects expired stock. Ward issues/returns maintain separate balances. Counts preserve both expected and actual quantity before recording any adjustment. Insufficient stock rolls back the operation.

Medication safety checks are workflow/data checks. This phase does not supply a drug interaction database, drug-class allergy inference, clinical dose recommendations or stock-packaging conversion rules. Stock units follow the configured catalogue unit. Corrections to administration are attributable addenda; the original outcome remains intact. Rounds are generated on demand; an unattended daily scheduler is not deployed. Staff credential/licence enforcement belongs to Phase 9. Institution-approved medication/consent policies and clinical acceptance remain required before real use.

## Verification and manual checklist

Integration tests cover prescribing/state history, scheduled-dose generation, duplicate administration rejection, PRN timing, allergy review, stock receipts/dispensing/ward return/counts, overdraw rollback, expiry rejection, facility isolation and database history protection. Frontend tests exercise prescription and eMAR forms and permission/context controls. Current totals and browser evidence are in [verification.md](verification.md).

- [ ] As a pharmacy officer, create a medication, supplier and valid batch; inspect the receipt ledger.
- [ ] As a prescriber, create/activate a prescription and check its complete dose, route, dates and instructions.
- [ ] Revise an order with a reason; verify prior versions remain and old due doses are cancelled.
- [ ] As a nurse, generate a day/week of rounds and filter by client, ward and time.
- [ ] Record given/refused/omitted/held/away outcomes; verify required reasons and dose rules.
- [ ] Retry a recorded dose and confirm rejection; add a correction and inspect the immutable original.
- [ ] Record PRN medication twice inside the prescribed minimum interval and confirm rejection.
- [ ] Dispense matching stock, issue to a ward, return/use stock and reconcile a count, including zero variance.
- [ ] Attempt expired dispensing and negative stock; verify no partial movement survives.
- [ ] Confirm ICT and finance accounts cannot prescribe, administer or read care records.
- [ ] Complete institutional medication, consent, licensing and deployment acceptance.
