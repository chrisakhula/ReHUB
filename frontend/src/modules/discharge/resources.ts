import type { Resource } from "../care/types";

export const dischargeResources: Resource[] = [
  {
    path: "/discharge/plans",
    title: "Discharge Plans",
    permission: "discharge.view",
    columns: [
      { key: "discharge_date", label: "Discharge Date" },
      { key: "admission_id", label: "Admission ID" },
      { key: "readiness_checked", label: "Ready" }
    ],
    fields: [
      { name: "admission_id", label: "Admission", type: "lookup", source: "/admissions", required: true },
      { name: "responsible_staff_id", label: "Responsible Staff", type: "lookup", source: "/users", required: true },
      { name: "readiness_checked", label: "Readiness Checked", type: "checkbox" },
      { name: "discharge_date", label: "Planned Date", type: "date" },
      { name: "summary", label: "Discharge Summary", type: "textarea" }
    ]
  },
  {
    path: "/discharge/aftercare",
    title: "Aftercare Cases",
    permission: "discharge.view",
    columns: [
      { key: "start_date", label: "Start Date" },
      { key: "client_id", label: "Client ID" },
      { key: "status", label: "Status" }
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients", required: true },
      { name: "assigned_staff_id", label: "Assigned Staff", type: "lookup", source: "/users", required: true },
      { name: "status", label: "Status", type: "select", options: ["active", "relapsed", "completed"] },
      { name: "start_date", label: "Start Date", type: "date" }
    ]
  }
];
