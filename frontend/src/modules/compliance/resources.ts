import type { Resource } from "../care/types";

export const complianceResources: Resource[] = [
  {
    path: "/compliance/registers",
    title: "Compliance Registers",
    permission: "compliance.view",
    columns: [
      { key: "category", label: "Category" },
      { key: "authority", label: "Authority" },
      { key: "reference_number", label: "Reference" },
      { key: "expiry_date", label: "Expiry Date" },
      { key: "status", label: "Status" }
    ],
    fields: [
      { name: "category", label: "Category", type: "select", options: ["NACADA", "FACILITY", "FIRE", "PHARMACY", "ODPC", "PROFESSIONAL", "INSURANCE"], required: true },
      { name: "authority", label: "Authority (e.g. NACADA, County)", type: "text", required: true },
      { name: "reference_number", label: "Reference Number", type: "text" },
      { name: "issue_date", label: "Issue Date", type: "date" },
      { name: "expiry_date", label: "Expiry Date", type: "date" },
      { name: "status", label: "Status", type: "select", options: ["ACTIVE", "EXPIRED", "IN_RENEWAL", "SUSPENDED"] },
      { name: "responsible_person_id", label: "Responsible Person", type: "lookup", source: "/users" },
      { name: "attachments_url", label: "Attachments URL", type: "text" },
      { name: "notes", label: "Notes", type: "textarea" }
    ],
    statusOptions: ["ACTIVE", "EXPIRED", "IN_RENEWAL", "SUSPENDED"]
  },
  {
    path: "/compliance/inspections",
    title: "Inspections & Audits",
    permission: "compliance.view",
    columns: [
      { key: "inspection_date", label: "Date" },
      { key: "title", label: "Title" },
      { key: "inspector_name", label: "Inspector" },
      { key: "passed", label: "Passed" },
      { key: "status", label: "Status" }
    ],
    fields: [
      { name: "register_id", label: "Compliance Register (Optional)", type: "lookup", source: "/compliance/registers" },
      { name: "title", label: "Title", type: "text", required: true },
      { name: "inspection_date", label: "Inspection Date", type: "date", required: true },
      { name: "inspector_name", label: "Inspector Name", type: "text", required: true },
      { name: "authority", label: "Authority", type: "text", required: true },
      { name: "findings", label: "Findings", type: "textarea" },
      { name: "corrective_actions", label: "Corrective Actions", type: "textarea" },
      { name: "passed", label: "Passed", type: "select", options: ["true", "false"] },
      { name: "status", label: "Status", type: "select", options: ["SCHEDULED", "COMPLETED", "FOLLOW_UP_REQUIRED"] }
    ],
    statusOptions: ["SCHEDULED", "COMPLETED", "FOLLOW_UP_REQUIRED"]
  }
];
