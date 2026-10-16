# Financial Agreements & Quotation Conversion

## 1. Overview
The Financial Agreement constitutes the formal admission-linked commercial contract establishing agreed programme charges, deposit schedules, inclusions, and exclusions.

## 2. Document References
- Quotations / Cost Estimates: `EST-YYYY-NNNNN` (e.g. `EST-2026-00001`)
- Financial Agreements: `FAG-YYYY-NNNNN` (e.g. `FAG-2026-00001`)
- Version tracking: `FAG-2026-00001 v1`, `FAG-2026-00001 v2`

## 3. Quotation Conversion Flow
1. Commercial quotation created with structured items (Programme, Lab tests, Medication).
2. Status moves: `DRAFT` → `ISSUED` → `ACCEPTED`.
3. Converting an accepted quotation creates `FinancialAgreement` (v1) automatically, copying:
   - Client reference
   - Agreed price and required deposit
   - Breakdown of inclusions and exclusions
   - Accepted by details and conversion timestamp
4. Quotations **do not post to the General Ledger** because they represent non-binding estimates.

## 4. Agreement Versioning & Immutability
- Accepted financial agreements are **never overwritten or destructively updated**.
- When terms change (e.g. extended stay, revised installment schedule, additional high-dependency care), a new version is created:
  - Previous version is marked `REVISED`.
  - New version increments `version` count (`v2`, `v3`).
  - Stores `parent_agreement_id` and mandatory `revision_reason`.
  - Requires maker-checker re-approval before entering `ACTIVE` status.
- Historical billing and invoices retain linkage to the version active during that billing cycle.

## 5. Maker-Checker Segregation
- The officer who creates or revises a financial agreement cannot approve it.
- Independent approval by a supervisor or Finance Manager is enforced with HTTP 403 segregation-of-duties checks.
