import type { Resource } from "../care/types";

export const staffResources: Resource[] = [
  {
    path: "/staff/profiles",
    title: "Staff Profiles",
    permission: "staff.view",
    columns: [
      { key: "employee_number", label: "Employee No." },
      { key: "designation", label: "Designation" },
      { key: "department", label: "Department" },
      { key: "employment_status", label: "Status" }
    ],
    fields: [
      { name: "user_id", label: "System User", type: "lookup", source: "/users", required: true },
      { name: "employee_number", label: "Employee Number", type: "text", required: true },
      { name: "designation", label: "Designation", type: "text", required: true },
      { name: "department", label: "Department", type: "text", required: true },
      { name: "qualifications", label: "Qualifications", type: "textarea" },
      { name: "professional_body", label: "Professional Body", type: "text" },
      { name: "licence_number", label: "Licence Number", type: "text" },
      { name: "licence_expiry", label: "Licence Expiry", type: "date" },
      { name: "employment_status", label: "Status", type: "select", options: ["ACTIVE", "ON_LEAVE", "TERMINATED"] },
      { name: "emergency_contact", label: "Emergency Contact", type: "text" }
    ],
    statusOptions: ["ACTIVE", "ON_LEAVE", "TERMINATED"]
  },
  {
    path: "/staff/shifts",
    title: "Shifts & Rosters",
    permission: "staff.view",
    columns: [
      { key: "shift_date", label: "Date" },
      { key: "staff_id", label: "Staff Profile ID" },
      { key: "shift_type", label: "Shift Type" },
      { key: "attended", label: "Attended" }
    ],
    fields: [
      { name: "staff_id", label: "Staff Profile", type: "lookup", source: "/staff/profiles", required: true },
      { name: "shift_date", label: "Shift Date", type: "date", required: true },
      { name: "shift_type", label: "Shift Type", type: "select", options: ["DAY", "NIGHT", "ON_CALL"], required: true },
      { name: "start_time", label: "Start Time", type: "date", required: true },
      { name: "end_time", label: "End Time", type: "date", required: true },
      { name: "attended", label: "Attended", type: "select", options: ["true", "false"] },
      { name: "notes", label: "Notes", type: "textarea" }
    ]
  }
];
