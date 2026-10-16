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
];
