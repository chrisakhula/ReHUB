import type { Resource } from "../care/types";

export const dischargeResources: Resource[] = [
  {
    path: "/discharge/plans",
    title: "Discharge Plans",
    permission: "discharge.view",
    columns: [
      { key: "created_at", label: "Date Created" },
      { key: "admission_id", label: "Admission" },
      { key: "discharge_type", label: "Type" },
      { key: "status", label: "Status" }
    ],
    fields: [
      { name: "admission_id", label: "Admission", type: "lookup", source: "/admissions", required: true },
      { name: "discharge_type", label: "Discharge Type", type: "select", options: ["PLANNED", "AMA", "TRANSFER", "DECEASED"] },
      { name: "goals_achieved", label: "Goals Achieved", type: "textarea" },
      { name: "unresolved_risks", label: "Unresolved Risks", type: "textarea" },
      { name: "relapse_prevention", label: "Relapse Prevention Plan", type: "textarea" },
      { name: "accommodation", label: "Accommodation/Housing", type: "text" },
      { name: "family_support", label: "Family Support", type: "text" },
      { name: "work_education", label: "Work/Education", type: "text" },
      { name: "support_groups", label: "Support Groups", type: "textarea" },
      { name: "appointments", label: "Appointments", type: "textarea" },
      { name: "referrals", label: "Referrals", type: "textarea" },
      { name: "emergency_plans", label: "Emergency Plans", type: "textarea" },
      { name: "medication_instructions", label: "Medication Instructions", type: "textarea" },
      { name: "belongings_returned", label: "Belongings Returned", type: "select", options: ["true", "false"] },
      { name: "status", label: "Status", type: "select", options: ["DRAFT", "PENDING_APPROVAL", "APPROVED", "DISCHARGED"] }
    ],
    statusOptions: ["DRAFT", "PENDING_APPROVAL", "APPROVED", "DISCHARGED"]
  },
  {
    path: "/discharge/aftercare",
    title: "Aftercare Cases",
    permission: "discharge.view",
    columns: [
      { key: "client_id", label: "Client ID" },
      { key: "start_date", label: "Start Date" },
      { key: "status", label: "Status" }
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients", required: true },
      { name: "assigned_staff_id", label: "Assigned Staff", type: "lookup", source: "/users" },
      { name: "start_date", label: "Start Date", type: "date", required: true },
      { name: "follow_up_intervals", label: "Follow-up Intervals (days)", type: "text" },
      { name: "status", label: "Status", type: "select", options: ["ACTIVE", "COMPLETED", "RELAPSED", "LOST_TO_FOLLOW_UP"] }
    ],
    statusOptions: ["ACTIVE", "COMPLETED", "RELAPSED", "LOST_TO_FOLLOW_UP"]
  },
  {
    path: "/discharge/relapse",
    title: "Relapse Records",
    permission: "discharge.view",
    columns: [
      { key: "date_of_relapse", label: "Date" },
      { key: "client_id", label: "Client ID" },
      { key: "substance", label: "Substance" },
      { key: "severity", label: "Severity" }
    ],
    fields: [
      { name: "client_id", label: "Client", type: "lookup", source: "/clients", required: true },
      { name: "date_of_relapse", label: "Date of Relapse", type: "date", required: true },
      { name: "substance", label: "Substance", type: "text", required: true },
      { name: "severity", label: "Severity", type: "select", options: ["SLIP", "FULL_RELAPSE"], required: true },
      { name: "triggers", label: "Triggers", type: "textarea" },
      { name: "circumstances", label: "Circumstances", type: "textarea" },
      { name: "consequences", label: "Consequences", type: "textarea" },
      { name: "protective_factors", label: "Protective Factors", type: "textarea" },
      { name: "intervention", label: "Intervention", type: "textarea" },
      { name: "clinical_review", label: "Clinical Review", type: "textarea" }
    ]
  }
];
