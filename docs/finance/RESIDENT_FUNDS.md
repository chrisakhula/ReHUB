# Resident Funds & Pocket Money Subledger

## 1. Overview
Resident Funds accounts (`RFA-YYYY-NNNNN`) track pocket money held in trust for inpatients during their stay. This money is **strictly non-revenue** and is treated as a custodial liability.

## 2. General Ledger Liability Mapping
- Pocket money deposits and withdrawals post atomically to GL Account `2200` (Client Deposits / Resident Funds Liability):
  - **Deposit**: Dr `1000` Cash (or `1010` M-Pesa) / Cr `2200` Liability.
  - **Withdrawal**: Dr `2200` Liability / Cr `1000` Cash.
- **Subledger Reconciliation**: Total active resident fund balances across all clients must strictly equal the credit balance of GL Account 2200.

## 3. Strict Non-Negative Balance Enforcement
- Resident accounts are prohibited from falling into a negative balance.
- If a withdrawal or purchase request exceeds `current_balance`, the transaction is immediately rejected with HTTP 400 (`Insufficient funds`).

## 4. Operational Operations
- `DEPOSIT`: Adding funds from family or resident personal cash.
- `WITHDRAWAL`: Cash given to resident for approved outings or personal needs.
- `PURCHASE`: Internal tuck shop or toiletries purchase on behalf of the resident.
- `RETURN_OF_FUNDS`: Full payout of remaining balance upon discharge.
- Each transaction records running balance, authorization, and receipt reference.
