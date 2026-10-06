import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { ErrorNotice, Pagination } from "../../components/Common";
import { CareWorkspace } from "../care/CareWorkspace";
import {
  check,
  choice,
  date,
  note,
  number,
  reason,
  staff,
  stamp,
} from "../care/fields";
import type { Field, Resource, Values } from "../care/types";

const notes: Field[] = [
  stamp("noted_at", "Note time", true),
  choice("shift", "Shift", ["DAY", "EVENING", "NIGHT"]),
  note("assessment", "Nursing assessment", true),
  note("note", "Nursing note", true),
  note("interventions", "Interventions"),
  note("escalation", "Escalation"),
  staff("escalated_to_id", "Escalated to"),
  check("high_risk", "High-risk flag"),
  stamp("observation_due_at", "Next observation due"),
];
const resources: Resource[] = [
  {
    title: "Nursing notes",
    historyPath: (r) => `/nursing/notes/${r.id}/revisions`,
    path: "/nursing/notes",
    permission: "nursing.view",
    writePermission: "nursing.record",
    admissionScoped: true,
    fields: notes,
    columns: [
      { key: "noted_at", label: "Time" },
      { key: "shift", label: "Shift" },
      { key: "high_risk", label: "High risk" },
      { key: "observation_due_at", label: "Observation due" },
      { key: "version", label: "Version" },
    ],
    actions: [
      {
        label: "Correct nursing note",
        permission: "nursing.record",
        path: (r) => `/nursing/notes/${r.id}/revisions`,
        fields: [
          ...notes,
          number("expected_version", "Expected version", true, 1),
          reason,
        ],
        defaults: (r) => ({ expected_version: r.version }),
        contextKeys: ["admission_id"],
      },
    ],
  },
  {
    title: "Observation chart",
    path: "/nursing/observations",
    permission: "nursing.view",
    writePermission: "nursing.record",
    admissionScoped: true,
    fields: [
      stamp("observed_at", "Observation time", true),
      number("sleep_hours", "Sleep hours", false, 0, 24),
      choice("appetite", "Appetite", [
        "GOOD",
        "FAIR",
        "POOR",
        "REFUSED",
        "NOT_ASSESSED",
      ]),
      textField("mood", "Mood", true),
      choice("hygiene", "Hygiene", [
        "INDEPENDENT",
        "PROMPTED",
        "ASSISTED",
        "REFUSED",
        "NOT_ASSESSED",
      ]),
      note("withdrawal_symptoms", "Withdrawal symptoms"),
      number("withdrawal_score", "Withdrawal score"),
      number("pain_score", "Pain score", false, 0, 10),
      note("interventions", "Interventions"),
      note("escalation", "Escalation"),
      stamp("next_observation_at", "Next observation"),
    ],
    columns: [
      { key: "observed_at", label: "Time" },
      { key: "sleep_hours", label: "Sleep" },
      { key: "appetite", label: "Appetite" },
      { key: "mood", label: "Mood" },
      { key: "pain_score", label: "Pain" },
      { key: "next_observation_at", label: "Next" },
    ],
  },
  {
    title: "Shift handover",
    path: "/nursing/handovers",
    permission: "nursing.view",
    writePermission: "nursing.record",
    admissionScoped: true,
    fields: [
      date("shift_date", "Shift date", true),
      choice("shift", "Shift", ["DAY", "EVENING", "NIGHT"]),
      note("summary", "Handover summary", true),
      note("outstanding_tasks", "Outstanding tasks"),
      choice("priority", "Priority", ["ROUTINE", "URGENT", "EMERGENCY"]),
    ],
    columns: [
      { key: "shift_date", label: "Date" },
      { key: "shift", label: "Shift" },
      { key: "priority", label: "Priority" },
      { key: "acknowledged_at", label: "Acknowledged" },
    ],
    actions: [
      {
        label: "Acknowledge handover",
        permission: "nursing.record",
        path: (r) => `/nursing/handovers/${r.id}/acknowledge`,
        fields: [],
        visible: (r) => !r.acknowledged_at,
      },
    ],
  },
];
function textField(name: string, label: string, required = false): Field {
  return { name, label, required };
}
export function NursingPage() {
  const [page, setPage] = useState(1);
  const dashboard = useQuery({
    queryKey: ["nursing-dashboard", page],
    queryFn: () => api<Values>(`/nursing/dashboard?page=${page}`),
  });
  return (
    <CareWorkspace
      title="Nursing station"
      description="Observations, attributable notes, escalation and shift continuity."
      resources={resources}
    >
      <ErrorNotice error={dashboard.error} />
      <div className="row g-3 mb-4">
        {[
          ["residents", "Current residents"],
          ["high_risk", "High risk (listed)"],
          ["observations_due", "Observations due (listed)"],
          ["outside_facility", "Outside facility (listed)"],
        ].map(([key, label]) => (
          <div className="col-sm-6 col-lg-3" key={key}>
            <div className="card card-body">
              <span>{label}</span>
              <strong className="fs-3">
                {dashboard.data
                  ? key === "residents"
                    ? (dashboard.data.meta as { total: number }).total
                    : (dashboard.data[key] as unknown[]).length
                  : "—"}
              </strong>
            </div>
          </div>
        ))}
      </div>
      <section className="card mb-4">
        <div className="card-header">
          <h2>Current resident worklist</h2>
        </div>
        <div className="table-responsive">
          <table className="table mb-0">
            <thead>
              <tr>
                <th>Client</th>
                <th>Admission</th>
                <th>Status</th>
                <th>High risk</th>
                <th>Observation due</th>
                <th>Care</th>
              </tr>
            </thead>
            <tbody>
              {((dashboard.data?.residents ?? []) as Values[]).map((row) => (
                <tr key={String(row.admission_id)}>
                  <td>{String(row.client_name)}</td>
                  <td>{String(row.admission_number)}</td>
                  <td>{String(row.status)}</td>
                  <td>{row.high_risk ? "Yes" : "No"}</td>
                  <td>
                    {row.observation_due_at
                      ? new Date(String(row.observation_due_at)).toLocaleString(
                          "en-KE",
                          { timeZone: "Africa/Nairobi" },
                        )
                      : "Not scheduled"}
                  </td>
                  <td>
                    <Link to={`/nursing?admission_id=${row.admission_id}`}>
                      Open care
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Pagination
          page={page}
          total={
            (dashboard.data?.meta as { total: number } | undefined)?.total ?? 0
          }
          onChange={setPage}
        />
      </section>
      <p>
        <Link to="/medication">Open medication rounds</Link> · Incident
        workflows are scheduled for Phase 7.
      </p>
    </CareWorkspace>
  );
}
