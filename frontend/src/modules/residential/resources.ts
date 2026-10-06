import type { Resource } from "../care/types";

export const residentialResources: Resource[] = [
  {
    path: "/residential/movements",
    title: "Resident Movements",
    permission: "residential.view",
    columns: [
      { key: "timestamp", label: "Date" },
      { key: "admission_id", label: "Admission ID" },
      { key: "movement_type", label: "Type" }
    ],
    fields: [
      { name: "admission_id", label: "Admission", type: "lookup", source: "/admissions", required: true },
      { name: "recorded_by_id", label: "Recorded By", type: "lookup", source: "/users", required: true },
      { name: "movement_type", label: "Movement Type", type: "select", options: ["leave", "hospital", "transfer", "awol", "return"], required: true },
      { name: "reason", label: "Reason", type: "text" },
      { name: "expected_return", label: "Expected Return", type: "date" }
    ]
  },
  {
    path: "/residential/incidents",
    title: "Incidents",
    permission: "residential.view",
    columns: [
      { key: "timestamp", label: "Date" },
      { key: "category", label: "Category" },
      { key: "severity", label: "Severity" },
      { key: "status", label: "Status" }
    ],
    fields: [
      { name: "reported_by_id", label: "Reported By", type: "lookup", source: "/users", required: true },
      { name: "category", label: "Category", type: "text", required: true },
      { name: "severity", label: "Severity", type: "select", options: ["low", "medium", "high", "critical"], required: true },
      { name: "status", label: "Status", type: "select", options: ["open", "investigating", "closed"] },
      { name: "description", label: "Description", type: "textarea", required: true }
    ],
    statusOptions: ["open", "investigating", "closed"]
  }
];
