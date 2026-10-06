import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Tabs, Tab } from "react-bootstrap";
import { PageHeader } from "../../components/Common";
import { ResourcePanel } from "../care/ResourcePanel";
import {
  admissionFields,
  choice,
  consentFields,
  lookup,
  propertyFields,
  reason,
  staff,
} from "../care/fields";
import type { Entity, Resource } from "../care/types";

export function AdmissionsPage() {
  const [params] = useSearchParams();
  const [selected, setSelected] = useState<Entity | null>(null);
  const base: Resource = {
    title: "Admissions",
    path: params.get("client_id")
      ? `/admissions?client_id=${params.get("client_id")}`
      : "/admissions",
    permission: "admission.view",
    writePermission: "admission.create",
    fields: admissionFields,
    defaults: { client_id: params.get("client_id") ?? "" },
    columns: [
      { key: "admission_number", label: "Admission" },
      { key: "client_name", label: "Client" },
      { key: "programme", label: "Programme" },
      { key: "admission_date", label: "Admitted" },
      { key: "status", label: "Status" },
    ],
    statusOptions: [
      "PENDING",
      "ACTIVE",
      "ON_LEAVE",
      "HOSPITALIZED",
      "AWOL",
      "DISCHARGE_PENDING",
    ],
    sortOptions: ["created_at", "admission_date", "admission_number"],
    actions: [
      {
        label: "Amend intake & acknowledgments",
        permission: "admission.update",
        path: (r) => `/admissions/${r.id}/intake`,
        method: "PUT",
        fields: [
          ...admissionFields.filter(
            (f) =>
              f.section === "Rights & requirements" ||
              f.section === "Search record",
          ),
          reason,
        ],
      },
      {
        label: "Change admission status",
        permission: "admission.update",
        path: (r) => `/admissions/${r.id}/status`,
        fields: [
          choice("status", "Next status", [
            "ACTIVE",
            "ON_LEAVE",
            "HOSPITALIZED",
            "AWOL",
            "DISCHARGE_PENDING",
          ]),
          reason,
        ],
      },
      {
        label: "Assign or transfer bed",
        permission: "residential.assign",
        path: (r) => `/admissions/${r.id}/bed`,
        fields: [
          lookup(
            "bed_id",
            "Available bed",
            "/residential/beds?status=AVAILABLE",
            true,
            undefined,
            ["name", "room_name", "wing_name"],
          ),
          reason,
        ],
      },
      {
        label: "Assign care team",
        permission: "admission.assign",
        path: (r) => `/admissions/${r.id}/assignments`,
        method: "PUT",
        fields: [
          ...[
            "assigned_counsellor_id",
            "assigned_clinician_id",
            "assigned_nurse_id",
            "primary_case_manager_id",
          ].map((n) => staff(n, n.replaceAll("_", " "))),
          reason,
        ],
      },
    ],
  };
  return (
    <>
      <PageHeader
        title="Admissions"
        description="Screened referrals become distinct care episodes. Activation requires consent, rights acknowledgment and a bed."
      />
      <ResourcePanel resource={base} onSelect={setSelected} />
      {selected && (
        <section className="mt-4">
          <div className="d-flex flex-wrap gap-2 mb-3">
            {[
              ["Assessments", "/assessments"],
              ["Rehabilitation", "/rehabilitation"],
              ["Clinical care", "/clinical"],
              ["Nursing", "/nursing"],
              ["Medication", "/medication"],
            ].map(([label, to]) => (
              <Link
                className="btn btn-outline-primary"
                key={to}
                to={`${to}?admission_id=${selected.id}`}
              >
                {label}
              </Link>
            ))}
          </div>
          <Tabs
            defaultActiveKey="consents"
            className="mb-3"
            mountOnEnter
            unmountOnExit
          >
            <Tab eventKey="consents" title="Consent decisions">
              <ResourcePanel
                key={selected.id}
                resource={{
                  title: "Consent decisions",
                  path: `/admissions/${selected.id}/consents`,
                  permission: "consent.view",
                  writePermission: "consent.create",
                  fields: consentFields,
                  columns: [
                    { key: "consent_type", label: "Type" },
                    { key: "decision", label: "Decision" },
                    { key: "version", label: "Text version" },
                    { key: "consent_date", label: "Date" },
                    { key: "withdrawn_at", label: "Withdrawal" },
                  ],
                  actions: [
                    {
                      label: "Withdraw consent",
                      permission: "consent.withdraw",
                      path: (r) => `/consents/${r.id}/withdraw`,
                      fields: [reason],
                      visible: (r) =>
                        r.decision === "GRANTED" && !r.withdrawn_at,
                    },
                  ],
                }}
              />
            </Tab>
            <Tab eventKey="property" title="Property">
              <ResourcePanel
                resource={{
                  title: "Property inventory",
                  path: `/admissions/${selected.id}/property`,
                  permission: "admission.view",
                  writePermission: "admission.property",
                  fields: propertyFields,
                  columns: [
                    { key: "description", label: "Description" },
                    { key: "category", label: "Category" },
                    { key: "quantity", label: "Quantity" },
                    { key: "returned_at", label: "Returned" },
                  ],
                  actions: [
                    {
                      label: "Return property",
                      permission: "admission.property",
                      path: (r) => `/property/${r.id}/return`,
                      fields: [reason],
                      visible: (r) => !r.returned_at,
                    },
                  ],
                }}
              />
            </Tab>
            <Tab eventKey="beds" title="Bed history">
              <ResourcePanel
                resource={{
                  title: "Bed assignment history",
                  path: `/admissions/${selected.id}/bed-history`,
                  permission: "residential.view",
                  columns: [
                    { key: "bed_id", label: "Bed" },
                    { key: "started_at", label: "Assigned" },
                    { key: "ended_at", label: "Ended" },
                    { key: "reason", label: "Reason" },
                  ],
                }}
              />
            </Tab>
            <Tab eventKey="history" title="Status history">
              <ResourcePanel
                resource={{
                  title: "Admission status history",
                  path: `/admissions/${selected.id}/history`,
                  permission: "admission.view",
                  columns: [
                    { key: "previous_status", label: "Before" },
                    { key: "new_status", label: "After" },
                    { key: "created_at", label: "When" },
                    { key: "reason", label: "Reason" },
                  ],
                }}
              />
            </Tab>
          </Tabs>
        </section>
      )}
    </>
  );
}
