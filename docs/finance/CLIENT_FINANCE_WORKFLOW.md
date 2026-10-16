# Client Finance Workflow Architecture & Lifecycle

## 1. Overview
ReHUB / ARS RMS Phase 26.6 establishes the complete end-to-end client financial lifecycle on top of the Phase 26.5 hardened General Ledger foundation.
The architecture spans from pre-admission financial assessment to final discharge statement and account closure.

```
Referral / Pre-Admission
        ↓
Financial Assessment (FAS-...)
        ↓
Quotation / Cost Estimate (EST-...)
        ↓
Payer / Sponsor Identification (SPN-...)
        ↓
Financial Agreement (FAG-... v1)
        ↓
Deposit / Initial Payment
        ↓
Admission Activation
        ↓
Programme / Package Billing
        ↓
Recurring & Clinical Extras
        ↓
Client Financial Account (Subledger)
        ↓
Invoices (INV-...)
        ↓
Payments (RCT-...) / Allocations
        ↓
Statements
        ↓
Payment Plans (PPL-...)
        ↓
Credit Notes / Refunds (RF-...) / Write-Offs
        ↓
Discharge Financial Review
        ↓
Financial Clearance (CLR-...)
        ↓
Final Statement
        ↓
Account Closure
```

## 2. Connected Subsystems
1. **Billing Core**: Canonical pricing, invoice items, and payment allocations.
2. **Accounts Receivable Subledger**: Client-level balance tracking reconciling to GL Account 1200.
3. **General Ledger**: Balanced double-entry journals posting atomically on revenue recognition and payment collection.
4. **Resident Pocket Money Subledger**: Trust liability tracking under GL Account 2200 (Client Deposits / Resident Funds Liability).
5. **M-Pesa Daraja Gateway**: Automated STK push, callback reconciliation, and supervised variance processing.

## 3. Core Safety & Accounting Constraints
- **Decimal-Only Monetary Math**: Exact 2-decimal fractional representation (`Decimal(val)` and `money()`), eliminating IEEE-754 floating-point errors.
- **Segregation of Duties**: Requester/creator cannot approve their own financial document (Financial Agreement, Payment Plan, Refund, Discharge Clearance, Credit Note, Write-Off).
- **Zero Raw UUID Exposure**: User interfaces and official documents exclusively display human-readable reference codes (`FAS`, `EST`, `FAG`, `PPL`, `RF`, `RFA`, `CLR`, `RCT`, `SPN`).
- **Zero Clinical Data Leakage**: Financial documents and statements present high-level billing categories (e.g. "Psychiatric Consultation", "Prescribed Medication", "Inpatient Accommodation") without exposing psychotherapy narratives, toxicology details, or risk notes.
