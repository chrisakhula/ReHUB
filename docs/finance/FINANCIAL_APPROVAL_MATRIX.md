# ReHUB / ARS RMS — Financial Approval Matrix & Segregation of Duties

## Purpose & Scope
This document defines the Role-Based Access Control (RBAC) authorization matrix, financial approval thresholds, and segregation of duties (maker-checker controls) implemented in ReHUB Phase 26.5.

Technical privileges are strictly decoupled from financial authority.

---

## 1. Role-Permission Matrix

| Functional Role | Key Assigned Permissions | Permitted Financial Actions | Prohibited Actions |
| :--- | :--- | :--- | :--- |
| **Reception** | `billing.view` | View invoices, view payment receipts, initiate admission fee inquiries | Cannot edit, discount, write-off, or approve |
| **Cashier** | `billing.collect_payment`, `billing.view`, `finance.view` | Collect cash/card/M-Pesa payments, issue payment receipts, prepare shift cash counts | Cannot approve own cash variances, cannot adjust invoices, cannot write-off |
| **Finance Officer** | `billing.view`, `billing.edit`, `billing.issue`, `billing.credit_note.create`, `billing.writeoff.request`, `finance.view`, `finance.reconcile` | Draft invoices, apply pre-issue discounts (≤10%), request credit notes, request debt write-offs, perform bank/M-Pesa reconciliation | Cannot approve own credit notes, cannot approve own write-offs, cannot approve cash variances |
| **Senior Finance / Finance Manager** | `finance.view`, `finance.edit`, `finance.approve`, `finance.reconcile`, `finance.close_period`, `billing.credit_note.approve`, `billing.writeoff.approve`, `finance.audit` | Approve expenses (≤ KES 50,000), approve cash variances, approve credit notes, approve write-offs (≤ KES 50,000), close fiscal periods, run integrity audits | Cannot approve write-offs or credit notes they originated (maker-checker) |
| **Facility Administrator / Management** | `finance.approve`, `finance.audit`, `finance.reopen_period` | Approve high-value expenses (> KES 50,000), approve high-value debt write-offs (> KES 50,000), authorize period reopening with audit justification | Cannot bypass double-entry GL balance controls |
| **System Administrator / ICT** | `system.view`, `system.manage`, `users.manage`, `audit.view` | System maintenance, backups, server observability, user provisioning | **STRICTLY PROHIBITED** from approving expenses, credit notes, write-offs, cash variances, or posting journals |
| **Super Administrator** | Technical break-glass authority | Emergency system-level restoration, infrastructure maintenance | Excluded from financial maker-checker workflows |

---

## 2. Maker-Checker Rules (Dual Authorization)

| Transaction Type | Maker (Initiator) | Checker (Approver) | Validation Enforced in Code |
| :--- | :--- | :--- | :--- |
| **Expense Voucher** | Finance Officer / Staff Requester | Finance Manager / Senior Finance | `approved_by != requester_id`, technical admin lockout |
| **High-Value Expense (> KES 50,000)** | Finance Officer / Requester | Facility Administrator / Director | Threshold check via `finance_expense_senior_approval_threshold` |
| **Cash Reconciliation Variance** | Cashier | Supervisor / Finance Manager | `approved_by != created_by`, non-zero variance requires `VARIANCE_REVIEW` |
| **Credit Note** | Billing Officer (`billing.credit_note.create`) | Finance Manager (`billing.credit_note.approve`) | `approved_by != created_by`, issued invoice is immutable |
| **Bad Debt Write-Off** | Billing Officer (`billing.writeoff.request`) | Finance Manager (`billing.writeoff.approve`) | `approved_by != requested_by`, status transition `PENDING_APPROVAL` → `APPROVED` |
| **High-Value Write-Off (> KES 50,000)** | Billing Officer | Senior Management / Director | Mandatory senior authorization check |
| **Pre-Issuance Discount (> 10%)** | Billing Officer | Finance Manager / Supervisor | `discount_approved_by` required when discount > 10% |

---

## 3. Threshold Configuration Standards

All thresholds are centrally defined and audit-logged:
- `finance_expense_senior_approval_threshold`: KES 50,000.00
- `cash_variance_manager_threshold`: KES 5,000.00
- `pricing_discount_manager_threshold`: 10.00%
- `write_off_senior_approval_threshold`: KES 50,000.00

Threshold modifications require administrative configuration privileges and create immutable security audit events.
