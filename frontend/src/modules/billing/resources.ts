import type { Resource } from "../care/types";

export const billingResources: Resource[] = [
  {
    path: "/billing/invoices",
    title: "Invoices",
    permission: "billing.view",
    columns: [
      { key: "issue_date", label: "Date" },
      { key: "client_id", label: "Client ID" },
      { key: "total_amount", label: "Amount" },
      { key: "status", label: "Status" }
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients", required: true },
      { name: "total_amount", label: "Total Amount", type: "number", required: true },
      { name: "status", label: "Status", type: "select", options: ["draft", "issued", "partial", "paid", "cancelled"] },
      { name: "due_date", label: "Due Date", type: "date" }
    ],
    statusOptions: ["draft", "issued", "partial", "paid", "cancelled"]
  }
];
