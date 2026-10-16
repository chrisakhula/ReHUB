# Payers, Sponsors & Split Billing

## 1. Entity Distinction
- **Client**: The patient receiving medical and psychosocial treatment.
- **Payer**: The individual or third-party entity legally/contractually liable for payments.
- **Sponsor**: Organizations (NGOs, Churches, Foundations, Corporate Employers, Government Bursaries) funding all or part of a client's care.

## 2. Split Payer Allocations
A single invoice can be split across multiple payers or sponsors via `billing_invoice_payer_allocations`:
```
Example Invoice: KES 200,000.00
├── Equity Foundation (Sponsor): 60% (KES 120,000.00)
└── Family Guarantor (Payer):   40% (KES  80,000.00)
Total Responsibility:           100% (KES 200,000.00)
```

### Validation Rules
- `Total percentage allocation <= 100.00%`. Over-allocations (e.g. 110%) are strictly rejected with HTTP 400.
- `Total allocated amount <= invoice total_amount`.
- Payments apply directly against individual payer allocations, tracking settled vs outstanding responsibility per guarantor without duplicating the underlying invoice.

## 3. Sponsor Statement & Isolation
- Sponsors can view consolidated statements (`SponsorStatementSummary`) showing all sponsored admissions, total billings, payments, and outstanding balances.
- **Privacy Wall**: Sponsor views never include psychotherapy notes, counselor summaries, or toxicology screening assays. They are limited strictly to commercial figures and billing descriptions.
