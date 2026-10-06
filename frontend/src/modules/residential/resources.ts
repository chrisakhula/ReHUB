import type { Resource } from "../care/types";

export const residentialResources: Resource[] = [
  {
    path: "/residential/movements",
    title: "Movements & Leave",
    permission: "residential.view",
    columns: [
      { key: "timestamp", label: "Date & Time" },
      { key: "admission_id", label: "Admission" },
      { key: "movement_type", label: "Type" },
      { key: "destination", label: "Destination" },
      { key: "expected_return", label: "Expected Return" }
    ],
    fields: [
      { name: "admission_id", label: "Admission", type: "lookup", source: "/admissions", required: true },
      { name: "movement_type", label: "Movement Type", type: "select", options: ["LEAVE", "HOSPITAL", "TRANSFER", "AWOL", "RETURN"], required: true },
      { name: "timestamp", label: "Timestamp", type: "date", required: true },
      { name: "expected_return", label: "Expected Return", type: "date" },
      { name: "destination", label: "Destination", type: "text" },
      { name: "reason", label: "Reason", type: "textarea" }
    ],
    statusOptions: ["LEAVE", "HOSPITAL", "TRANSFER", "AWOL", "RETURN"]
  },
  {
    path: "/residential/incidents",
    title: "Incidents & Reporting",
    permission: "residential.view",
    columns: [
      { key: "timestamp", label: "Date & Time" },
      { key: "category", label: "Category" },
      { key: "severity", label: "Severity" },
      { key: "location", label: "Location" },
      { key: "status", label: "Status" }
    ],
    fields: [
      { name: "category", label: "Category", type: "select", options: ["MEDICAL", "BEHAVIORAL", "SECURITY", "FACILITY"], required: true },
      { name: "severity", label: "Severity", type: "select", options: ["LOW", "MEDIUM", "HIGH", "CRITICAL"], required: true },
      { name: "location", label: "Location", type: "text" },
      { name: "timestamp", label: "Timestamp", type: "date", required: true },
      { name: "description", label: "Description", type: "textarea", required: true },
      { name: "status", label: "Status", type: "select", options: ["OPEN", "INVESTIGATING", "CLOSED"] }
    ],
    statusOptions: ["OPEN", "INVESTIGATING", "CLOSED"]
  },
  {
    path: "/residential/safeguarding",
    title: "Safeguarding Records",
    permission: "safeguarding.view",
    columns: [
      { key: "client_id", label: "Client" },
      { key: "concern_type", label: "Concern" },
      { key: "vulnerable_group", label: "Group" },
      { key: "escalation_level", label: "Escalation" },
      { key: "status", label: "Status" }
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients", required: true },
      { name: "concern_type", label: "Concern Type", type: "select", options: ["ABUSE", "NEGLECT", "EXPLOITATION", "SELF_HARM"], required: true },
      { name: "vulnerable_group", label: "Vulnerable Group", type: "select", options: ["MINOR", "ELDERLY", "DISABLED"], required: true },
      { name: "description", label: "Description", type: "textarea", required: true },
      { name: "escalation_level", label: "Escalation", type: "select", options: ["INTERNAL", "EXTERNAL_AUTHORITY"] },
      { name: "escalated_to", label: "Escalated To", type: "text" },
      { name: "follow_up_action", label: "Follow-up Action", type: "textarea" },
      { name: "status", label: "Status", type: "select", options: ["OPEN", "CLOSED"] }
    ]
  },
  {
    path: "/residential/grievances",
    title: "Complaints & Grievances",
    permission: "residential.view",
    columns: [
      { key: "created_at", label: "Date" },
      { key: "submitted_by", label: "Submitted By" },
      { key: "category", label: "Category" },
      { key: "status", label: "Status" }
    ],
    fields: [
      { name: "submitted_by", label: "Submitted By (Name)", type: "text", required: true },
      { name: "category", label: "Category", type: "select", options: ["FOOD", "STAFF", "FACILITY", "PEER", "OTHER"], required: true },
      { name: "description", label: "Description", type: "textarea", required: true },
      { name: "status", label: "Status", type: "select", options: ["RECEIVED", "INVESTIGATING", "RESOLVED"] },
      { name: "resolution", label: "Resolution", type: "textarea" },
      { name: "corrective_action", label: "Corrective Action", type: "textarea" }
    ],
    statusOptions: ["RECEIVED", "INVESTIGATING", "RESOLVED"]
  },
  {
    path: "/residential/visitors",
    title: "Approved Visitors",
    permission: "residential.view",
    columns: [
      { key: "name", label: "Name" },
      { key: "relationship_to_client", label: "Relationship" },
      { key: "client_id", label: "Client ID" },
      { key: "approved", label: "Approved" }
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients", required: true },
      { name: "name", label: "Visitor Name", type: "text", required: true },
      { name: "relationship_to_client", label: "Relationship", type: "text", required: true },
      { name: "id_number", label: "ID Number", type: "text" },
      { name: "contact_phone", label: "Contact Phone", type: "text" },
      { name: "approved", label: "Approved", type: "select", options: ["true", "false"] }
    ]
  }
];
