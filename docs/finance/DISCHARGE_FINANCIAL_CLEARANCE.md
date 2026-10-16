# Discharge Financial Clearance & Exceptions

## 1. Safety Principles & Separation of Concerns
Clinical discharge status must **never** be blocked or superseded by financial considerations. ReHUB maintains three strictly independent statuses:
1. **Clinical Discharge Status**: Medical/psychiatric determination that treatment is complete or client is fit for release.
2. **Financial Clearance Status**: Commercial review of account balances (`CLR-YYYY-NNNNN`).
3. **Administrative Closure Status**: Operational record archiving.

## 2. Clearance Statuses
- `NOT_REVIEWED`: Pre-discharge baseline.
- `PENDING`: Final charges captured, awaiting finance review.
- `CLEARED`: All charges settled, net balance = 0.
- `PAYMENT_PLAN`: Outstanding balance covered by an approved post-discharge installment plan (`PPL-...`).
- `AUTHORIZED_EXCEPTION`: Approved release with outstanding debt under supervisory exception.
- `REFUND_DUE`: Client has an unrefunded credit balance.

## 3. Authorized Financial Exceptions
If a client must be released with outstanding debt without a payment plan:
- Finance captures:
  - Exact outstanding debt amount
  - Compelling institutional reason (e.g. court order, family emergency, compassionate release)
  - Designated collection owner responsible for debt recovery
  - Independent supervisory approval
- **Accounting Invariant**: Outstanding balance is **never silently zeroed out**. Accounts receivable balance remains intact on subledger and GL until collected or formally written off.
