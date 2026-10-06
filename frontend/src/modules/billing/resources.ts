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
  }
];
