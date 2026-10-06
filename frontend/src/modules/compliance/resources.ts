import type { Resource } from "../care/types";

export const complianceResources: Resource[] = [
  {
    path: "/compliance/licences",
    title: "Licences & Certificates",
    permission: "compliance.view",
    columns: [
      { key: "name", label: "Name" },
      { key: "authority", label: "Authority" },
      { key: "expiry_date", label: "Expiry Date" },
      { key: "status", label: "Status" }
    ],
    fields: [
      { name: "name", label: "Licence Name", type: "text", required: true },
      { name: "authority", label: "Issuing Authority", type: "text", required: true },
      { name: "reference_number", label: "Reference Number", type: "text" },
      { name: "issue_date", label: "Issue Date", type: "date" },
      { name: "expiry_date", label: "Expiry Date", type: "date" },
      { name: "status", label: "Status", type: "select", options: ["active", "expired", "renewed"] }
    ]
  },
  {
    path: "/compliance/audits",
    title: "Inspections & Audits",
    permission: "compliance.view",
    columns: [
      { key: "audit_date", label: "Date" },
      { key: "title", label: "Title" },
      { key: "auditor", label: "Auditor" },
      { key: "passed", label: "Passed" }
    ],
    fields: [
      { name: "title", label: "Audit Title", type: "text", required: true },
      { name: "auditor", label: "Auditor/Inspector Name", type: "text", required: true },
      { name: "audit_date", label: "Audit Date", type: "date" },
      { name: "passed", label: "Passed", type: "checkbox" },
      { name: "findings", label: "Findings", type: "textarea" }
    ]
  }
];
