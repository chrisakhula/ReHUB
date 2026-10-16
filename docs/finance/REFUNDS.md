# Client Refund Workflow & Accounting Mappings

## 1. Overview
Refunds (`RF-YYYY-NNNNN`) manage credit balances arising from unused admission deposits or authorized billing reversals.

## 2. Maker-Checker Segregation
- The officer who requests a refund cannot approve or process it.
- Approval requires independent Finance Manager authorization (`billing.refund.approve`).
- Self-approval attempts return HTTP 403 segregation of duties errors.

## 3. General Ledger Source-Based Posting
Refunds post balanced double-entry journals atomically upon approval. The debit account is selected dynamically based on `source_type`:

### Case A: Unused Client Deposit
- **Source**: `CLIENT_DEPOSIT`
- **Debit**: GL Account `2200` (Client Deposits / Resident Funds Liability)
- **Credit**: GL Account `1030` (Bank) or `1010` (M-Pesa) / `1000` (Cash)

### Case B: Revenue Adjustment / Overbilling Reversal
- **Source**: `REVENUE_REVERSAL`
- **Debit**: GL Account `4000` (Programme Revenue)
- **Credit**: GL Account `1030` (Bank) or `1010` (M-Pesa) / `1000` (Cash)

## 4. Atomicity
If General Ledger journal creation fails (e.g. fiscal period locked or unbalanced lines), the entire refund transaction rolls back atomically.
