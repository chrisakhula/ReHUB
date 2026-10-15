# Safaricom M-Pesa Production Acceptance & Commissioning Report

> **System:** ReHUB Rehabilitation Management System (Billing & Finance Engine)  
> **Document Reference:** COMM-MPESA-2026-10-14  
> **Date:** 2026-10-14  
> **Target Production Release:** v1.0.0 (Current: v1.0.0-rc1)  
> **Gate Status:** `CONDITIONAL`  
> **Condition:** Awaiting live Safaricom Daraja production credentials and institutional Paybill activation.  

---

## 1. Executive Summary

The Safaricom M-Pesa integration in ReHUB provides automated resident fee settlement via C2B Webhook and STK Push (`CustomerPayBillOnline`), direct invoice allocation, reconciliation review workspaces, and balanced double-entry General Ledger posting.

All internal software engineering, security hardening, database idempotency constraints, failure handling, and simulation tests have **PASSED 100%**. In adherence to commissioning rules, this gate remains **`CONDITIONAL`** until a genuine low-value live transaction is executed on Safaricom's production network.

---

## 2. Production Configuration Support Verification

The application supports full runtime configuration via environment variables without hardcoded secrets:

| Variable | Scope & Purpose | Production Requirement | Verified Status |
| :--- | :--- | :--- | :---: |
| `MPESA_ENVIRONMENT` | API target (`sandbox` or `production`) | Must be set to `production` | **Verified** |
| `MPESA_CONSUMER_KEY` | Daraja API app consumer key | Provided by Safaricom portal | **Verified** |
| `MPESA_CONSUMER_SECRET` | Daraja API app consumer secret | Provided by Safaricom portal | **Verified** |
| `MPESA_SHORTCODE` | Business Paybill / Till Number | Institutional Paybill | **Verified** |
| `MPESA_PASSKEY` | STK Push LNM online passkey | Generated in Daraja portal | **Verified** |
| `MPESA_CALLBACK_URL` | Public HTTPS callback endpoint | E.g. `https://rehub.facility.ke/api/v1/billing/mpesa/callback` | **Verified** |
| `MPESA_TIMEOUT_URL` | Queue timeout endpoint | E.g. `https://rehub.facility.ke/api/v1/billing/mpesa/timeout` | **Verified** |
| `MPESA_RESULT_URL` | C2B Validation / Confirmation URL | Public HTTPS endpoint | **Verified** |

### Configuration Security Checks
- [x] **No hardcoded secrets:** Zero hardcoded API keys or passkeys exist in the codebase.
- [x] **Git protection:** `.env` and `.env.local` are explicitly listed in `.gitignore` and omitted from commits.
- [x] **Runtime ingestion:** `Settings` uses Pydantic `BaseSettings` with `extra="ignore"` and runtime resolution.
- [x] **Secret protection in logs:** Log formatters strictly redact or omit authorization headers and payload secrets.

---

## 3. M-Pesa Security & Idempotency Audit

Prior to live execution, the following security and architectural controls were verified:

1. **Idempotency Guard:**
   - Database constraint on `mpesa_transactions.transaction_reference` (`TransID`) and `checkout_request_id`.
   - Repeated callbacks return `{"ResultCode": 0, "ResultDesc": "Already processed"}` without duplicate payment records or double journal postings.
2. **System Actor Attribution:**
   - Automated webhook events are non-human attributed using `get_system_actor(db, facility_id)` (`M-Pesa Integration System Actor`), ensuring complete audit traceability without zero-UUID placeholders.
3. **Double-Entry General Ledger Balance:**
   - Standard receivable settlement posts automatically:
     - `Dr 1010` (M-Pesa Control Account / Clearing) = Amount
     - `Cr 1200` (Accounts Receivable) = Amount
   - Enforced: `Total Debit == Total Credit`.
4. **Reconciliation Lifecycle:**
   - Direct match: Invoices with matching `AccountReference` are allocated automatically (`AUTO_RECONCILED`).
   - Unmatched / Overpayment: Unmatched transactions transition to `UNMATCHED` status and surface in the Finance Reconciliation Workspace (`/billing/mpesa/reconciliation`) for dual-signoff manual matching.
5. **Partial Payments:**
   - Allocates paid amount against invoice balance; invoice status updates to `PARTIAL`; remaining balance tracked.
6. **Failure Resilience:**
   - Cancelled requests (ResultCode `1032`) and timeouts (ResultCode `1037`) cleanly mark transaction `CANCELLED`/`FAILED` without corrupting invoice or ledger balances.

---

## 4. Test Verification Evidence

### Automated Test Suite Execution
Executed in pre-commissioning environment against test database:
- `app/tests/test_mpesa_daraja.py::test_normalize_phone_number` → **PASSED**
- `app/tests/test_mpesa_daraja.py::test_mpesa_stk_push_and_callback_flow` → **PASSED**
- `app/tests/test_mpesa_daraja.py::test_manual_mpesa_reconciliation` → **PASSED**
- `app/tests/test_e2e_scenarios.py::test_e2e_scenario_3_mpesa_billing_reconciliation` → **PASSED**

---

## 5. Live Production Test Template (Pending Final Action)

Upon population of live production credentials into `.env`, the following low-value verification test (KES 10.00) must be executed and recorded:

```text
================================================================================
CONTROLLED LIVE M-PESA PRODUCTION TEST TEMPLATE
================================================================================
Test Reference:           MPESA-LIVE-TEST-001
Test Date & Time:         [Pending Execution]
Payer Phone:              2547XXXXXXXX
Invoice Number:           INV-2026-XXXXX
Requested Amount:         KES 10.00
MerchantRequestID:        [Captured from Safaricom STK Response]
CheckoutRequestID:        [Captured from Safaricom STK Response]
Safaricom TransID:        [e.g. QK71XXXXXX from SMS / Callback]
Callback Status:          [200 OK Received]
Payment Record ID:        [UUID]
Allocation Record ID:     [UUID]
Invoice Status Update:    [PENDING -> PARTIAL / PAID]
General Ledger Journal:   [Journal Reference: MPESA-QK71XXXXXX]
                          Dr 1010 (M-Pesa Control):        KES 10.00
                          Cr 1200 (Accounts Receivable):   KES 10.00
                          Balance Check: Dr == Cr (PASSED)
Reconciliation State:     AUTO_RECONCILED
Audit Event ID:           [UUID]
================================================================================
```

---

## 6. Acceptance Sign-Off

| Role | Name | Designation | Decision | Date |
| :--- | :--- | :--- | :---: | :--- |
| **Technical Lead** | Cleophas | Lead Systems Engineer | **VERIFIED (PREREQUISITES PASS)** | 2026-10-14 |
| **Finance Controller** | [Pending Institutional Assignment] | Head of Finance | **CONDITIONAL** | Pending |

### Final Gate Status:
**`CONDITIONAL`**  
*Reason:* Awaiting live Safaricom production credentials (`MPESA_CONSUMER_KEY`, `MPESA_CONSUMER_SECRET`, `MPESA_PASSKEY`, `MPESA_SHORTCODE`) and Paybill network routing.
