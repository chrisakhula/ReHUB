# ReHUB / ARS RMS — Phase 26.5: Finance Safety, Accounting Integrity & Control Remediation

## Executive Summary
Phase 26.5 remediates 7 critical financial control defects identified during the comprehensive read-only finance audit of the ReHUB accounting engine. This phase hardens the core accounting, billing, and general ledger foundation to make it internally consistent, auditable, and production-defensible before Phase 26.6 client finance lifecycle expansions.

---

## 1. Monetary Standard & Decimal Policy (P0-1)

### The Defect
Previous billing calculations used standard Python `float()` and mixed rounding logic across services, risking floating-point drift, IEEE 754 precision issues, and subtle rounding divergence between invoice subtotals, tax/discount lines, and General Ledger balanced entries.

### The Remediation
- **Canonical Quantization Helper**: Created `app.core.money` containing:
  - `MONEY_QUANTUM = Decimal("0.01")`
  - Canonical helper function `money(value) -> Decimal` using `ROUND_HALF_UP`.
- **Database Column Audit**:
  - All monetary columns in `billing` and `finance` schemas (`invoices`, `invoice_items`, `payments`, `payment_allocations`, `expenses`, `supplier_invoices`, `supplier_payments`, `journal_entry_lines`, `cash_reconciliations`, `billing_credit_notes`, `billing_write_offs`) utilize PostgreSQL `NUMERIC(14, 2)` or `NUMERIC(12, 2)`.
  - Disallowed floating-point types (`REAL`, `FLOAT`, `DOUBLE PRECISION`) for financial fields.
- **Ledger Comparison Standards**:
  - GL balance validation enforces exact Decimal equivalence: `money(total_debit) == money(total_credit)`.
  - Zero-tolerance ledger balancing maintains strict double-entry integrity.

---

## 2. Technical Segregation of Duties (P0-2)

### The Principle: Technical Authority ≠ Financial Authority
A System Administrator or ICT Administrator maintains the system infrastructure, backups, and user provisioning, but must **never** hold operational business financial approval privileges.

### Remediations
1. **Revocation Forward Migration (`vv1234567890`)**:
   - Stripped `finance.approve`, `finance.close_period`, `finance.reopen_period`, `finance.reconcile`, and `billing.credit_note.approve` from the `System Administrator` and `Super Administrator` roles.
2. **Explicit Code Lockout**:
   - `FinanceLedgerService.approve_expense` explicitly checks and rejects technical administrative roles (`System Administrator`, `Super Administrator`, `ICT Administrator`) from approving operational expenses, even if assigned auxiliary permissions.
3. **Threshold-Based Senior Approvals**:
   - Standard expenses require `Finance Manager` or `Senior Finance Officer` approval.
   - High-value expenses exceeding `finance_expense_senior_approval_threshold` (default KES 50,000.00) require explicit management or executive board authorization.
   - Break-glass technical intervention requires formal institutional audit event logging with justification.

---

## 3. Cash Variance Supervisory Gate (P0-3)

### The Defect
Previously, submitting a cash reconciliation immediately auto-posted cash shortages or overages directly to the General Ledger without management or supervisory review, allowing cashiers to effectively self-authorize variances.

### Remediation Workflow
```
Cashier Physical Count
         ↓
Variance Calculated
         ↓
Variance == 0 ? ─── Yes ───► Status: BALANCED
         │
         No
         ↓
Status: VARIANCE_REVIEW
         ↓
Cashier Submits Explanation
         ↓
Supervisor / Finance Manager Investigation
         ↓
Approved / Rejected by Independent Supervisor
         ↓ (On Approval)
Atomic GL Posting:
  • Shortage: Dr Cash Shortage Expense (6600) / Cr Cash on Hand (1000)
  • Overage:  Dr Cash on Hand (1000) / Cr Cash Overage Income (4300)
         ↓
Status: POSTED
```
- **Maker-Checker Enforcement**: The cashier who prepared the reconciliation (`created_by`) is strictly prohibited from approving their own variance (`approved_by != created_by`).
- **Configurable Variance Threshold**: Variances exceeding `cash_variance_manager_threshold` (default KES 5,000.00) escalate to `Finance Manager` authorization.

---

## 4. Issued Invoice Immutability & Credit Note Workflow (P0-4)

### The Defect
Billing adjustments previously mutated `invoice.total_amount` in place after issuance, destroying historical audit trails and causing divergence with the Accounts Receivable General Ledger journal.

### Remediation
1. **Financial Immutability**:
   - Once an invoice is in status `ISSUED`, `PARTIALLY_PAID`, `PAID`, or `OVERDUE`, direct modification of line items, tax, discounts, or total amounts is strictly forbidden.
2. **Activated Credit Note Engine**:
   - Credit notes must be created for post-issuance balance reductions with structured reasons:
     - `BILLING_ERROR`
     - `DUPLICATE_CHARGE`
     - `SERVICE_NOT_DELIVERED`
     - `APPROVED_DISCOUNT`
     - `EARLY_DISCHARGE_ADJUSTMENT`
     - `OTHER` (mandatory explanation required).
3. **Credit Note Accounting**:
   - When approved, credit notes generate atomic General Ledger entries:
     - **Debit**: Patient Service Revenue / Revenue Adjustment (Account 4000)
     - **Credit**: Accounts Receivable (Account 1200)
   - Invoice balance and status (`PAID`, `PARTIAL`, `ISSUED`) recalculate atomically based on net remaining balance after applied credit notes.
4. **Credit Note Maker-Checker**:
   - The creator of the credit note (`billing.credit_note.create`) cannot self-approve (`billing.credit_note.approve`).

---

## 5. Atomic Billing & GL Posting (P0-5)

### The Defect
GL posting errors were frequently caught in `try...except Exception:` blocks with `logger.warning(...)` or `pass`, leaving the business transaction committed while the General Ledger journal silently vanished.

### Remediation
- **Atomic Transaction Boundaries**:
  - The business entity mutation (invoice issuance, payment recording, credit note approval, debt write-off, cash variance approval) and its corresponding General Ledger journal entry execute within a **single database transaction boundary**.
- **Exception Propagation**:
  - Replaced swallowed exceptions with strict transaction rollback and propagation of `FinancialPostingError`.
  - Returns HTTP 422 with clean user-safe messaging:
    `"The financial transaction could not be completed because accounting posting failed. No changes were saved."`
  - Zero partial financial states can occur.

---

## 6. Bad Debt Write-Off Maker-Checker (P0-6)

### The Defect
Write-off requests previously set the caller directly as the approver and immediately posted to the GL, bypassing dual control.

### Remediation
1. **Two-Stage Workflow**:
   - Request created in `PENDING_APPROVAL` status by billing officer (`billing.writeoff.request`).
   - Requires independent approver with `billing.writeoff.approve` (`approved_by != requested_by`).
2. **Threshold Governance**:
   - Write-offs exceeding KES 50,000.00 require executive/senior finance officer authorization.
3. **Atomic Accounting**:
   - Upon approval, posts:
     - **Debit**: Bad Debt Expense (Account 6000)
     - **Credit**: Accounts Receivable (Account 1200)
   - Invoice marked `WRITTEN_OFF`. If GL fails, invoice remains unpaid/issued.

---

## 7. Pricing Discounts vs Post-Issuance Credits (P0-7)

### Clear Separation of Concerns
1. **Pre-Issuance Pricing Discounts**:
   - Applied while invoice is in `DRAFT` status.
   - Discounts > 10% require supervisory approval recorded in `discount_approved_by`.
2. **Post-Issuance Adjustments**:
   - Direct mutation of issued invoices is rejected.
   - Any post-issuance reduction must follow the Credit Note workflow.
