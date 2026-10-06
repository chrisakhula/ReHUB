import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Alert, Form } from "react-bootstrap";
import { api, save } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";
import { CareWorkspace } from "../care/CareWorkspace";
import { ResourcePanel } from "../care/ResourcePanel";
import { RecordForm } from "../care/RecordForm";
import {
  check,
  choice,
  date,
  lookup,
  note,
  number,
  reason,
  stamp,
  strings,
  text,
} from "../care/fields";
import { todayEAT } from "../care/validation";
import type { Field, Resource } from "../care/types";

const prescriptionFields: Field[] = [
  lookup(
    "medication_id",
    "Medication",
    "/medication/catalogue",
    true,
    "Medication",
    ["generic_name", "strength", "formulation", "dose_unit"],
  ),
  number("dose", "Prescribed dose", true, 0.001, undefined, "Medication"),
  text("dose_unit", "Dose unit (match catalogue)", true, "Medication"),
  lookup(
    "route_id",
    "Medication route",
    "/medication/routes",
    true,
    "Medication",
    ["name"],
  ),
  text("frequency", "Frequency instructions", true, "Schedule"),
  number(
    "frequency_hours",
    "Fixed interval (hours; leave empty for daily times)",
    false,
    1,
    168,
    "Schedule",
  ),
  {
    ...strings("scheduled_times", "Daily times (HH:MM, EAT)", "Schedule"),
    default: ["08:00"],
  },
  stamp("start_at", "Start", true, "Schedule"),
  stamp("stop_at", "Stop", false, "Schedule"),
  check(
    "prn",
    "PRN: only as required (clear daily times/interval)",
    "Schedule",
  ),
  number(
    "prn_min_interval_hours",
    "Minimum PRN interval in hours",
    false,
    1,
    168,
    "Schedule",
  ),
  note("indication", "Indication", true, "Instructions & review"),
  note("instructions", "Instructions", false, "Instructions & review"),
  note(
    "allergy_override_reason",
    "Prescriber allergy-review override reason",
    false,
    "Instructions & review",
  ),
];
const statusFields = [
  choice("status", "Next state", [
    "ACTIVE",
    "SUSPENDED",
    "DISCONTINUED",
    "COMPLETED",
  ]),
  number("expected_version", "Expected prescription version", true, 1),
  reason,
];
export const rx: Resource = {
  title: "Prescriptions",
  path: "/medication/prescriptions",
  permission: "medication.view",
  writePermission: "medication.prescribe",
  admissionScoped: true,
  fields: prescriptionFields,
  columns: [
    { key: "generic_name", label: "Medication" },
    { key: "strength", label: "Strength" },
    { key: "dose", label: "Dose" },
    { key: "dose_unit", label: "Unit" },
    { key: "frequency", label: "Frequency" },
    { key: "status", label: "Status" },
  ],
  historyPath: (r) => `/medication/prescriptions/${r.id}/history`,
  statusOptions: ["DRAFT", "ACTIVE", "SUSPENDED", "DISCONTINUED", "COMPLETED"],
  actions: [
    {
      label: "Change prescription state",
      permission: "medication.prescribe",
      path: (r) => `/medication/prescriptions/${r.id}/status`,
      fields: statusFields,
      defaults: (r) => ({ expected_version: r.version }),
      visible: (r) => !["DISCONTINUED", "COMPLETED"].includes(String(r.status)),
    },
    {
      label: "Revise prescription",
      permission: "medication.prescribe",
      path: (r) => `/medication/prescriptions/${r.id}`,
      method: "PUT",
      fields: [
        ...prescriptionFields,
        number("expected_version", "Expected prescription version", true, 1),
        reason,
      ],
      contextKeys: ["admission_id"],
      defaults: (r) => ({ expected_version: r.version }),
      visible: (r) => !["DISCONTINUED", "COMPLETED"].includes(String(r.status)),
    },
  ],
};
export const adminFields: Field[] = [
  text("prescription_id", "Prescription ID", true),
  text("dose_id", "Scheduled dose ID"),
  stamp("administered_at", "Actual administration / outcome time", true),
  choice("status", "Outcome", [
    "GIVEN",
    "REFUSED",
    "OMITTED",
    "HELD",
    "NOT_AVAILABLE",
    "PATIENT_AWAY",
    "PRN",
  ]),
  number("actual_dose", "Actual dose (zero/blank if not given)", false, 0),
  note("reason", "Reason (required when not given or dose differs)"),
  note("notes", "Notes"),
];
const administered: Resource = {
  historyPath: (r) => `/medication/administrations/${r.id}/addenda`,
  title: "Administration history",
  path: "/medication/administrations",
  permission: "medication.view",
  columns: [
    { key: "administered_at", label: "Actual time" },
    { key: "prescribed_dose", label: "Prescribed" },
    { key: "actual_dose", label: "Actual" },
    { key: "dose_unit", label: "Unit" },
    { key: "status", label: "Outcome" },
  ],
  admissionScoped: true,
  actions: [
    {
      label: "Add correction",
      permission: "medication.administer",
      path: (r) => `/medication/administrations/${r.id}/addenda`,
      fields: [note("correction", "Correction / clarification", true), reason],
    },
  ],
};
function Rounds() {
  const auth = useAuth();
  const [params] = useSearchParams();
  const admission = params.get("admission_id") ?? "";
  const cache = useQueryClient();
  const [message, setMessage] = useState("");
  const [day, setDay] = useState(todayEAT());
  const [round, setRound] = useState("");
  const [ward, setWard] = useState("");
  const wards = useQuery({
    queryKey: ["round-wings"],
    queryFn: () =>
      api<{ items: { id: string; name: string }[] }>(
        "/residential/wings?page_size=100",
      ),
    enabled: auth.can("residential.view"),
  });
  return (
    <section className="mb-4">
      <h2 className="mb-3">Medication rounds</h2>
      {message && (
        <Alert variant="success" onClose={() => setMessage("")} dismissible>
          {message}
        </Alert>
      )}
      {auth.can("medication.administer") && (
        <div className="card card-body mb-3">
          <h3 className="fs-6">Generate scheduled doses</h3>
          <p className="text-secondary small">
            Generate up to seven days from active prescriptions. Repeated
            generation preserves existing outcomes.
          </p>
          <RecordForm
            fields={[
              date("start", "From date", true),
              date("end", "To date", true),
            ]}
            submitLabel="Generate medication rounds"
            onSubmit={async (data) => {
              const result = await save<{ doses_created: number }>(
                `/medication/schedule${admission ? `?admission_id=${admission}` : ""}`,
                data,
              );
              setMessage(`${result.doses_created} scheduled doses created.`);
              await cache.invalidateQueries();
            }}
          />
        </div>
      )}
      <div className="d-flex gap-3 mb-3">
        <Form.Group controlId="emar-day">
          <Form.Label>Round date</Form.Label>
          <Form.Control
            type="date"
            value={day}
            onChange={(e) => setDay(e.target.value)}
          />
        </Form.Group>
        <Form.Group controlId="emar-time">
          <Form.Label>Scheduled time (EAT)</Form.Label>
          <Form.Control
            type="time"
            value={round}
            onChange={(e) => setRound(e.target.value)}
          />
        </Form.Group>
      </div>
      {auth.can("residential.view") && (
        <Form.Group controlId="round-ward" className="mb-3">
          <Form.Label>Ward / wing</Form.Label>
          <Form.Select value={ward} onChange={(e) => setWard(e.target.value)}>
            <option value="">All wards</option>
            {wards.data?.items.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </Form.Select>
        </Form.Group>
      )}
      <ResourcePanel
        key={`${admission}-${day}-${round}-${ward}`}
        context={{ admission_id: admission }}
        resource={{
          title: "Medication due",
          sortOptions: ["scheduled_at", "created_at"],
          path: `/medication/due?day=${day}${round ? `&round_time=${round}` : ""}${ward ? `&ward_id=${ward}` : ""}`,
          permission: "medication.view",
          admissionScoped: true,
          columns: [
            { key: "client_name", label: "Client" },
            { key: "admission_number", label: "Admission" },
            { key: "medication", label: "Medication" },
            { key: "strength", label: "Strength" },
            { key: "prescribed_dose", label: "Dose" },
            { key: "route_name", label: "Route" },
            { key: "scheduled_at", label: "Scheduled" },
          ],
          actions: [
            {
              label: "Record administration outcome",
              permission: "medication.administer",
              path: () => "/medication/administrations",
              fields: adminFields,
              defaults: (r) => ({
                prescription_id: r.prescription_id,
                dose_id: r.id,
                actual_dose: r.prescribed_dose,
                status: "GIVEN",
              }),
            },
          ],
        }}
      />
    </section>
  );
}
export function MedicationPage() {
  return (
    <CareWorkspace
      title="Medication & eMAR"
      description="Prescriber-controlled orders, scheduled rounds and attributable medication outcomes."
      resources={[rx, administered]}
    >
      <Rounds />
    </CareWorkspace>
  );
}
