import type { Resource } from "../care/types";

export const billingResources: Resource[] = [
  {
    path: "/billing/invoices",
    title: "Invoices",
    permission: "billing.view",
    columns: [
      { key: "invoice_number", label: "Invoice #" },
      { key: "issue_date", label: "Date" },
      { key: "client_id", label: "Client ID" },
      { key: "total_amount", label: "Amount" },
      { key: "status", label: "Status" }
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients", required: true },
      { name: "payer_id", label: "Payer", type: "lookup", source: "/billing/payers" },
      { name: "invoice_number", label: "Invoice Number", type: "text", required: true },
      { name: "issue_date", label: "Issue Date", type: "date", required: true },
      { name: "due_date", label: "Due Date", type: "date", required: true },
      { name: "status", label: "Status", type: "select", options: ["DRAFT", "ISSUED", "PARTIAL", "PAID", "CANCELLED", "WRITTEN_OFF"] }
    ],
    statusOptions: ["DRAFT", "ISSUED", "PARTIAL", "PAID", "CANCELLED", "WRITTEN_OFF"]
  },
  {
    path: "/billing/payments",
    title: "Payments & Receipts",
    permission: "billing.view",
    columns: [
      { key: "payment_date", label: "Date" },
      { key: "client_id", label: "Client" },
      { key: "amount", label: "Amount" },
      { key: "payment_method", label: "Method" },
      { key: "status", label: "Status" }
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients" },
      { name: "payer_id", label: "Payer", type: "lookup", source: "/billing/payers" },
      { name: "amount", label: "Amount", type: "number", required: true },
      { name: "payment_method", label: "Method", type: "select", options: ["CASH", "MPESA", "CARD", "TRANSFER"], required: true },
      { name: "transaction_reference", label: "Reference", type: "text", required: true },
      { name: "payment_date", label: "Date", type: "date", required: true }
    ],
    statusOptions: ["PENDING", "COMPLETED", "FAILED", "REFUNDED"]
  },
  {
    path: "/billing/payers",
    title: "Payers & Sponsors",
    permission: "billing.view",
    columns: [
      { key: "name", label: "Name" },
      { key: "payer_type", label: "Type" },
      { key: "contact_person", label: "Contact Person" },
      { key: "contact_phone", label: "Phone" }
    ],
    fields: [
      { name: "name", label: "Name", type: "text", required: true },
      { name: "payer_type", label: "Type", type: "select", options: ["INSURANCE", "PRIVATE", "CORPORATE", "SPONSOR"], required: true },
      { name: "contact_person", label: "Contact Person", type: "text" },
      { name: "contact_email", label: "Email", type: "text" },
      { name: "contact_phone", label: "Phone", type: "text" },
      { name: "billing_address", label: "Address", type: "textarea" }
    ]
  },
  {
    path: "/billing/services",
    title: "Service Catalogue",
    permission: "billing.view",
    columns: [
      { key: "code", label: "Code" },
      { key: "name", label: "Name" },
      { key: "category", label: "Category" }
    ],
    fields: [
      { name: "code", label: "Code", type: "text", required: true },
      { name: "name", label: "Name", type: "text", required: true },
      { name: "category", label: "Category", type: "text", required: true },
      { name: "description", label: "Description", type: "textarea" }
    ]
  },
  {
    path: "/billing/credit-notes",
    title: "Credit Notes",
    permission: "billing.view",
    writePermission: "billing.credit_note.create",
    columns: [
      { key: "credit_note_number", label: "CN #" },
      { key: "invoice_id", label: "Invoice ID" },
      { key: "amount", label: "Amount" },
      { key: "reason_code", label: "Reason Code" },
      { key: "status", label: "Status" },
      { key: "created_at", label: "Date" },
    ],
    fields: [
      { name: "invoice_id", label: "Invoice ID", type: "text", required: true },
      { name: "amount", label: "Amount (KES)", type: "number", required: true },
      {
        name: "reason_code",
        label: "Reason Code",
        type: "select",
        options: [
          "BILLING_ERROR",
          "DUPLICATE_CHARGE",
          "SERVICE_NOT_DELIVERED",
          "APPROVED_DISCOUNT",
          "EARLY_DISCHARGE_ADJUSTMENT",
          "OTHER",
        ],
        required: true,
      },
      { name: "reason", label: "Explanation / Notes", type: "textarea" },
    ],
    statusOptions: ["DRAFT", "ISSUED", "REJECTED"],
    actions: [
      {
        label: "Approve Credit Note",
        permission: "billing.credit_note.approve",
        path: (record) => `/billing/credit-notes/${record.id}/approve`,
        fields: [
          { name: "approval_notes", label: "Approval Notes", type: "textarea" },
        ],
        visible: (record) => record.status === "DRAFT",
      },
      {
        label: "Reject Credit Note",
        permission: "billing.credit_note.approve",
        path: (record) => `/billing/credit-notes/${record.id}/reject`,
        fields: [
          { name: "approval_notes", label: "Rejection Reason", type: "textarea", required: true },
        ],
        visible: (record) => record.status === "DRAFT",
      },
    ],
  },
  {
    path: "/billing/writeoffs",
    title: "Bad Debt Write-Offs",
    permission: "billing.view",
    writePermission: "billing.writeoff.request",
    columns: [
      { key: "reference_code", label: "Ref #" },
      { key: "invoice_id", label: "Invoice ID" },
      { key: "amount", label: "Amount" },
      { key: "status", label: "Status" },
      { key: "reason", label: "Reason" },
      { key: "created_at", label: "Date" },
    ],
    fields: [
      { name: "invoice_id", label: "Invoice ID", type: "text", required: true },
      { name: "amount", label: "Amount (KES)", type: "number", required: true },
      { name: "reason", label: "Reason for Write-Off", type: "textarea", required: true },
    ],
    statusOptions: ["DRAFT", "APPROVED", "REJECTED"],
    actions: [
      {
        label: "Approve Write-Off",
        permission: "billing.writeoff.approve",
        path: (record) => `/billing/writeoffs/${record.id}/approve`,
        fields: [
          { name: "approval_notes", label: "Approval Notes", type: "textarea" },
        ],
        visible: (record) => record.status === "DRAFT",
      },
      {
        label: "Reject Write-Off",
        permission: "billing.writeoff.approve",
        path: (record) => `/billing/writeoffs/${record.id}/reject`,
        fields: [
          { name: "approval_notes", label: "Rejection Reason", type: "textarea", required: true },
        ],
        visible: (record) => record.status === "DRAFT",
      },
    ],
  },
  {
    path: "/billing/financial-assessments",
    title: "Financial Assessments",
    permission: "billing.view",
    writePermission: "billing.create",
    columns: [
      { key: "reference_code", label: "Assessment #" },
      { key: "client_id", label: "Client" },
      { key: "proposed_programme", label: "Proposed Programme" },
      { key: "primary_payer_type", label: "Primary Payer" },
      { key: "estimated_programme_cost", label: "Est. Cost (KES)" },
      { key: "deposit_required", label: "Deposit Req. (KES)" },
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients", required: true },
      { name: "proposed_programme", label: "Proposed Programme", type: "text", required: true },
      { name: "expected_length_of_stay_days", label: "Expected Stay (Days)", type: "number", required: true },
      { name: "expected_admission_date", label: "Expected Admission Date", type: "date", required: true },
      {
        name: "primary_payer_type",
        label: "Primary Payer Type",
        type: "select",
        options: ["SELF", "FAMILY", "EMPLOYER", "CORPORATE", "INSURANCE", "NGO", "CHURCH", "GOVERNMENT", "OTHER"],
        required: true,
      },
      { name: "primary_payer_name", label: "Primary Payer Name", type: "text", required: true },
      { name: "estimated_programme_cost", label: "Estimated Programme Cost", type: "number", required: true },
      { name: "deposit_required", label: "Deposit Required", type: "number", required: true },
      { name: "credit_terms", label: "Credit Terms", type: "text" },
      { name: "installment_preference", label: "Installment Preference", type: "text" },
      { name: "financial_notes", label: "Financial Notes", type: "textarea" },
    ],
  },
  {
    path: "/billing/quotations",
    title: "Quotations / Estimates",
    permission: "billing.view",
    writePermission: "billing.create",
    columns: [
      { key: "reference_code", label: "Quotation #" },
      { key: "client_id", label: "Client" },
      { key: "programme_name", label: "Programme" },
      { key: "total_amount", label: "Total (KES)" },
      { key: "deposit_required", label: "Deposit Req." },
      { key: "status", label: "Status" },
      { key: "valid_until", label: "Valid Until" },
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients", required: true },
      { name: "programme_name", label: "Programme Name", type: "text", required: true },
      { name: "duration_days", label: "Duration (Days)", type: "number", required: true },
      { name: "deposit_required", label: "Deposit Required", type: "number", required: true },
      { name: "valid_until", label: "Valid Until", type: "date", required: true },
      { name: "terms_and_conditions", label: "Terms & Conditions", type: "textarea" },
      { name: "notes", label: "Notes", type: "textarea" },
    ],
    statusOptions: ["DRAFT", "ISSUED", "ACCEPTED", "REJECTED", "EXPIRED", "CONVERTED"],
    actions: [
      {
        label: "Issue Quotation",
        permission: "billing.create",
        path: (record) => `/billing/quotations/${record.id}/issue`,
        fields: [],
        visible: (record) => record.status === "DRAFT",
      },
      {
        label: "Accept Quotation",
        permission: "billing.create",
        path: (record) => `/billing/quotations/${record.id}/accept`,
        fields: [
          { name: "accepted_by", label: "Accepted By (Full Name)", type: "text", required: true },
        ],
        visible: (record) => record.status === "ISSUED",
      },
      {
        label: "Convert to Financial Agreement",
        permission: "billing.create",
        path: (record) => `/billing/quotations/${record.id}/convert`,
        fields: [],
        visible: (record) => record.status === "ACCEPTED",
      },
    ],
  },
  {
    path: "/billing/agreements",
    title: "Financial Agreements",
    permission: "billing.view",
    writePermission: "billing.create",
    columns: [
      { key: "reference_code", label: "Agreement #" },
      { key: "version", label: "Ver" },
      { key: "client_id", label: "Client" },
      { key: "programme_name", label: "Programme" },
      { key: "agreed_price", label: "Agreed Price" },
      { key: "deposit_amount", label: "Deposit" },
      { key: "status", label: "Status" },
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients", required: true },
      { name: "programme_name", label: "Programme Name", type: "text", required: true },
      { name: "agreed_price", label: "Agreed Price (KES)", type: "number", required: true },
      { name: "deposit_amount", label: "Deposit Amount (KES)", type: "number", required: true },
      { name: "installment_terms", label: "Installment Terms", type: "text" },
      { name: "credit_terms", label: "Credit Terms", type: "text" },
      { name: "inclusions", label: "Inclusions", type: "textarea" },
      { name: "exclusions", label: "Exclusions", type: "textarea" },
      { name: "refund_terms", label: "Refund Terms", type: "textarea" },
      { name: "effective_date", label: "Effective Date", type: "date", required: true },
      { name: "notes", label: "Notes", type: "textarea" },
    ],
    statusOptions: ["DRAFT", "PENDING_ACCEPTANCE", "ACTIVE", "REVISED", "COMPLETED", "CANCELLED"],
    actions: [
      {
        label: "Approve Agreement",
        permission: "billing.agreement.approve",
        path: (record) => `/billing/agreements/${record.id}/approve`,
        fields: [
          { name: "notes", label: "Approval Notes", type: "textarea" },
        ],
        visible: (record) => record.status === "PENDING_ACCEPTANCE" || record.status === "DRAFT",
      },
    ],
  },
  {
    path: "/billing/payment-plans",
    title: "Payment Plans",
    permission: "billing.view",
    writePermission: "billing.create",
    columns: [
      { key: "reference_code", label: "Plan #" },
      { key: "client_id", label: "Client" },
      { key: "total_amount", label: "Total Amount" },
      { key: "number_of_installments", label: "Installments" },
      { key: "status", label: "Status" },
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients", required: true },
      { name: "total_amount", label: "Total Amount (KES)", type: "number", required: true },
      { name: "number_of_installments", label: "Number of Installments", type: "number", required: true },
      { name: "notes", label: "Notes", type: "textarea" },
    ],
    statusOptions: ["DRAFT", "ACTIVE", "ON_TRACK", "OVERDUE", "DEFAULTED", "COMPLETED", "CANCELLED"],
    actions: [
      {
        label: "Approve Payment Plan",
        permission: "billing.payment_plan.approve",
        path: (record) => `/billing/payment-plans/${record.id}/approve`,
        fields: [],
        visible: (record) => record.status === "DRAFT",
      },
    ],
  },
  {
    path: "/billing/refunds",
    title: "Client Refunds",
    permission: "billing.view",
    writePermission: "billing.refund.request",
    columns: [
      { key: "reference_code", label: "Refund #" },
      { key: "client_id", label: "Client" },
      { key: "amount", label: "Amount (KES)" },
      { key: "source_type", label: "Source" },
      { key: "refund_method", label: "Method" },
      { key: "status", label: "Status" },
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients", required: true },
      { name: "amount", label: "Refund Amount (KES)", type: "number", required: true },
      { name: "reason", label: "Refund Reason", type: "textarea", required: true },
      {
        name: "source_type",
        label: "Source of Funds",
        type: "select",
        options: ["CLIENT_DEPOSIT", "REVENUE_REVERSAL"],
        required: true,
      },
      {
        name: "refund_method",
        label: "Refund Method",
        type: "select",
        options: ["BANK", "MPESA", "CASH"],
        required: true,
      },
      { name: "transaction_reference", label: "Payment Reference", type: "text" },
    ],
    statusOptions: ["PENDING_APPROVAL", "APPROVED", "PAID", "REJECTED", "CANCELLED"],
    actions: [
      {
        label: "Approve Refund",
        permission: "billing.refund.approve",
        path: (record) => `/billing/refunds/${record.id}/approve`,
        fields: [
          { name: "notes", label: "Approval Notes", type: "textarea" },
        ],
        visible: (record) => record.status === "PENDING_APPROVAL",
      },
    ],
  },
  {
    path: "/billing/resident-funds",
    title: "Resident Pocket Money",
    permission: "billing.view",
    writePermission: "resident_funds.deposit",
    columns: [
      { key: "reference_code", label: "Account #" },
      { key: "client_id", label: "Client" },
      { key: "current_balance", label: "Balance (KES)" },
      { key: "is_active", label: "Active" },
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients", required: true },
    ],
    actions: [
      {
        label: "Deposit Pocket Money",
        permission: "resident_funds.deposit",
        path: (record) => `/billing/resident-funds/${record.id}/deposit`,
        fields: [
          { name: "amount", label: "Deposit Amount (KES)", type: "number", required: true },
          { name: "description", label: "Purpose / Description", type: "text", required: true },
          { name: "receipt_reference", label: "Receipt Reference", type: "text" },
          {
            name: "payment_method",
            label: "Payment Method",
            type: "select",
            options: ["CASH", "MPESA", "BANK"],
            required: true,
          },
        ],
      },
      {
        label: "Withdraw Pocket Money",
        permission: "resident_funds.withdraw",
        path: (record) => `/billing/resident-funds/${record.id}/withdraw`,
        fields: [
          { name: "amount", label: "Withdrawal Amount (KES)", type: "number", required: true },
          { name: "description", label: "Purchase Description / Reason", type: "text", required: true },
          {
            name: "transaction_type",
            label: "Transaction Type",
            type: "select",
            options: ["WITHDRAWAL", "PURCHASE", "RETURN_OF_FUNDS"],
            required: true,
          },
        ],
      },
    ],
  },
  {
    path: "/billing/discharge-clearances",
    title: "Discharge Financial Clearance",
    permission: "billing.view",
    writePermission: "billing.discharge_clearance",
    columns: [
      { key: "reference_code", label: "Clearance #" },
      { key: "client_id", label: "Client" },
      { key: "outstanding_balance", label: "Outstanding (KES)" },
      { key: "status", label: "Status" },
      { key: "has_payment_plan", label: "Has Plan" },
      { key: "is_authorized_exception", label: "Exception" },
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients", required: true },
    ],
    statusOptions: ["NOT_REVIEWED", "PENDING", "CLEARED", "PAYMENT_PLAN", "AUTHORIZED_EXCEPTION", "REFUND_DUE"],
    actions: [
      {
        label: "Approve Clearance",
        permission: "billing.discharge_clearance",
        path: (record) => `/billing/discharge-clearances/${record.id}/approve`,
        fields: [
          { name: "notes", label: "Approval Notes", type: "textarea" },
        ],
        visible: (record) => record.status === "PENDING" || record.status === "AUTHORIZED_EXCEPTION" || record.status === "PAYMENT_PLAN",
      },
    ],
  },
  {
    path: "/billing/sponsors",
    title: "Sponsors & Donors",
    permission: "billing.view",
    writePermission: "billing.create",
    columns: [
      { key: "reference_code", label: "Sponsor #" },
      { key: "name", label: "Organization / Family" },
      { key: "sponsor_type", label: "Type" },
      { key: "credit_limit", label: "Credit Limit" },
      { key: "balance", label: "Balance" },
    ],
    fields: [
      { name: "name", label: "Sponsor Name", type: "text", required: true },
      {
        name: "sponsor_type",
        label: "Type",
        type: "select",
        options: ["FAMILY", "EMPLOYER", "NGO", "CHURCH", "INSURANCE", "CORPORATE", "GOVERNMENT", "OTHER"],
        required: true,
      },
      { name: "contact_person", label: "Contact Person", type: "text" },
      { name: "email", label: "Email", type: "text" },
      { name: "phone", label: "Phone", type: "text" },
      { name: "billing_address", label: "Billing Address", type: "textarea" },
      { name: "credit_limit", label: "Credit Limit (KES)", type: "number", required: true },
    ],
  },
];
