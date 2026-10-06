import {
  choice,
  date,
  note,
  number,
  reason,
  staff,
  stamp,
  text,
} from "../care/fields";
import type { Field, Resource } from "../care/types";

export const encounterFields: Field[] = [
  stamp("encounter_at", "Encounter time", true, "Encounter"),
  staff("clinician_id", "Responsible clinician", false, "Encounter"),
  choice(
    "encounter_type",
    "Encounter type",
    ["ADMISSION", "ROUTINE", "FOLLOW_UP", "EMERGENCY"],
    true,
    "ROUTINE",
    "Encounter",
  ),
  note(
    "presenting_complaint",
    "Presenting complaint",
    true,
    "History & examination",
  ),
  note("medical_history", "Medical history", false, "History & examination"),
  note(
    "physical_examination",
    "Physical examination",
    false,
    "History & examination",
  ),
  note("diagnosis", "Diagnoses", false, "Assessment & plan"),
  note("assessment", "Assessment", false, "Assessment & plan"),
  note("plan", "Plan", false, "Assessment & plan"),
  stamp("follow_up_at", "Follow-up", false, "Assessment & plan"),
  note("emergency_action", "Emergency action", false, "Assessment & plan"),
];
export const vitalFields: Field[] = [
  stamp("observed_at", "Observation time", true),
  ...Object.entries({
    systolic: "Systolic BP (mmHg)",
    diastolic: "Diastolic BP (mmHg)",
    pulse: "Pulse (/min)",
    respiratory_rate: "Respiration (/min)",
    temperature: "Temperature (°C)",
    oxygen_saturation: "SpO₂ (%)",
    weight: "Weight (kg)",
    height: "Height (cm)",
    blood_glucose: "Blood glucose (mmol/L)",
    pain_score: "Pain (0–10)",
  }).map(([n, l]) => number(n, l)),
  note("notes", "Measurement notes"),
];
export const clinicalResources: Resource[] = [
  {
    title: "Clinical encounters",
    historyPath: (r) => `/clinical/encounters/${r.id}/revisions`,
    path: "/clinical/encounters",
    permission: "clinical.view",
    writePermission: "clinical.create_note",
    fields: encounterFields,
    admissionScoped: true,
    columns: [
      { key: "encounter_at", label: "Encounter" },
      { key: "encounter_type", label: "Type" },
      { key: "presenting_complaint", label: "Presentation" },
      { key: "diagnosis", label: "Diagnosis" },
      { key: "version", label: "Version" },
    ],
    actions: [
      {
        label: "Correct encounter",
        permission: "clinical.create_note",
        path: (r) => `/clinical/encounters/${r.id}/revisions`,
        fields: [
          ...encounterFields,
          number("expected_version", "Expected version", true, 1),
          reason,
        ],
        contextKeys: ["admission_id"],
        defaults: (r) => ({ expected_version: r.version }),
      },
    ],
  },
  {
    title: "Problem list",
    path: "/clinical/problems",
    permission: "clinical.view",
    writePermission: "clinical.create_note",
    clientScoped: true,
    fields: [
      text("diagnosis", "Diagnosis / problem", true),
      text("code", "Diagnosis code"),
      date("onset_date", "Onset"),
    ],
    columns: [
      { key: "diagnosis", label: "Problem" },
      { key: "code", label: "Code" },
      { key: "onset_date", label: "Onset" },
      { key: "status", label: "Status" },
    ],
    actions: [
      {
        label: "Update problem status",
        permission: "clinical.create_note",
        path: (r) => `/clinical/problems/${r.id}`,
        method: "PATCH",
        fields: [
          choice("status", "Status", ["ACTIVE", "RESOLVED"]),
          note("resolution", "Resolution"),
          reason,
        ],
      },
    ],
  },
  {
    title: "Allergies",
    path: "/clinical/allergies",
    permission: "clinical.view",
    writePermission: "clinical.create_note",
    clientScoped: true,
    fields: [
      text("substance", "Allergen", true),
      text("reaction", "Reaction", true),
      choice("severity", "Severity", ["MILD", "MODERATE", "SEVERE", "UNKNOWN"]),
    ],
    columns: [
      { key: "substance", label: "Allergen" },
      { key: "reaction", label: "Reaction" },
      { key: "severity", label: "Severity" },
      { key: "status", label: "Status" },
    ],
    actions: [
      {
        label: "Update allergy status",
        permission: "clinical.create_note",
        path: (r) => `/clinical/allergies/${r.id}`,
        method: "PATCH",
        fields: [
          choice("status", "Status", [
            "ACTIVE",
            "INACTIVE",
            "ENTERED_IN_ERROR",
          ]),
          reason,
        ],
      },
    ],
  },
  {
    title: "Vitals",
    path: "/clinical/vitals",
    permission: "clinical.view",
    writePermission: "clinical.record_vitals",
    admissionScoped: true,
    fields: vitalFields,
    columns: [
      { key: "observed_at", label: "Observed" },
      { key: "systolic", label: "Systolic" },
      { key: "diastolic", label: "Diastolic" },
      { key: "pulse", label: "Pulse" },
      { key: "temperature", label: "Temperature" },
      { key: "oxygen_saturation", label: "SpO₂" },
    ],
  },
  {
    title: "Medical orders",
    path: "/clinical/orders",
    permission: "clinical.view",
    writePermission: "clinical.manage_orders",
    admissionScoped: true,
    fields: [
      choice("order_type", "Order type", [
        "MEDICAL",
        "INVESTIGATION",
        "REFERRAL",
        "FOLLOW_UP",
        "OBSERVATION",
      ]),
      note("description", "Order", true),
      text("destination", "Destination"),
      choice("priority", "Priority", ["ROUTINE", "URGENT", "EMERGENCY"]),
      stamp("due_at", "Due time"),
    ],
    columns: [
      { key: "order_type", label: "Type" },
      { key: "description", label: "Order" },
      { key: "due_at", label: "Due" },
      { key: "priority", label: "Priority" },
      { key: "status", label: "Status" },
    ],
    actions: [
      {
        label: "Complete or cancel order",
        permission: "clinical.manage_orders",
        path: (r) => `/clinical/orders/${r.id}`,
        method: "PATCH",
        fields: [
          choice("status", "Status", ["COMPLETED", "CANCELLED"]),
          note("completion_note", "Completion note", true),
          reason,
        ],
        visible: (r) => r.status === "PENDING",
      },
    ],
  },
];
export const labResources: Resource[] = [
  {
    title: "Laboratory investigations",
    readLinks: [
      {
        label: "Download latest PDF",
        permission: "lab.view",
        path: (r) =>
          `/lab/attachments/${String((r.attachments as { id: string }[] | undefined)?.at(-1)?.id)}`,
        visible: (r) =>
          Array.isArray(r.attachments) && r.attachments.length > 0,
      },
    ],
    path: "/lab/requests",
    permission: "lab.view",
    writePermission: "lab.order",
    admissionScoped: true,
    fields: [
      text("test", "Investigation / test", true),
      note("indication", "Indication", true),
      text("provider", "Laboratory provider", true),
      text("specimen_type", "Specimen type", true),
      stamp("specimen_at", "Specimen collection"),
      choice("priority", "Priority", ["ROUTINE", "URGENT", "EMERGENCY"]),
    ],
    columns: [
      { key: "test", label: "Test" },
      { key: "provider", label: "Provider" },
      { key: "specimen_at", label: "Specimen" },
      { key: "priority", label: "Priority" },
      { key: "status", label: "Status" },
    ],
    actions: [
      {
        label: "Record result",
        permission: "lab.result",
        path: (r) => `/lab/requests/${r.id}/results`,
        fields: [
          stamp("resulted_at", "Result date", true),
          note("result", "Result", true),
          text("units", "Units"),
          text("reference_range", "Reference range"),
          choice("abnormal_flag", "Flag", [
            "NORMAL",
            "LOW",
            "HIGH",
            "CRITICAL",
            "ABNORMAL",
            "UNKNOWN",
          ]),
          note(
            "correction_reason",
            "Correction reason (required for revised results)",
          ),
        ],
      },
      {
        label: "Review latest result",
        permission: "clinical.manage_orders",
        path: (r) =>
          `/lab/results/${String((r.results as { id: string }[] | undefined)?.at(-1)?.id)}/review`,
        fields: [note("review_note", "Review note", true)],
        visible: (r) => Array.isArray(r.results) && r.results.length > 0,
      },
      {
        label: "Attach external PDF",
        permission: "lab.result",
        path: (r) => `/lab/requests/${r.id}/attachments`,
        fields: [
          {
            ...text("filename", "File name ending in .pdf", true),
            default: "result.pdf",
          },
          {
            name: "content_base64",
            label: "PDF file (maximum 5 MB)",
            type: "file",
            required: true,
          },
        ],
      },
    ],
  },
];
export const toxicologyResources: Resource[] = [
  {
    title: "Toxicology tests",
    path: "/toxicology/tests",
    permission: "lab.view",
    writePermission: "lab.result",
    admissionScoped: true,
    fields: [
      stamp("test_at", "Test time", true),
      note("reason", "Test reason", true),
      text("sample_type", "Sample type", true),
      {
        name: "results",
        label: "Substance result",
        type: "array",
        required: true,
        fields: [
          text("substance", "Substance", true),
          choice("result", "Result", [
            "POSITIVE",
            "NEGATIVE",
            "INCONCLUSIVE",
            "NOT_TESTED",
          ]),
          text("concentration", "Concentration"),
        ],
      },
      text("confirmatory_test", "Confirmatory test"),
      text("confirmatory_result", "Confirmatory result"),
      staff("staff_id", "Testing staff"),
      choice("acknowledgement", "Client acknowledgement", [
        "ACKNOWLEDGED",
        "DECLINED",
        "UNABLE",
        "PENDING",
      ]),
      note("acknowledgement_note", "Acknowledgement notes"),
      note("follow_up_action", "Follow-up action", true),
    ],
    columns: [
      { key: "test_at", label: "Tested" },
      { key: "sample_type", label: "Sample" },
      { key: "results", label: "Substances" },
      { key: "acknowledgement", label: "Acknowledgement" },
    ],
  },
];
