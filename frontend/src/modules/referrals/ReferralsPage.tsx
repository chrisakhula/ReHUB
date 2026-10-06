import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeader } from "../../components/Common";
import { ResourcePanel } from "../care/ResourcePanel";
import {
  choice,
  reason,
  referralFields,
  screeningFields,
} from "../care/fields";
import type { Entity, Resource } from "../care/types";

export function ReferralsPage() {
  const [params] = useSearchParams();
  const [selected, setSelected] = useState<Entity | null>(null);
  const resource: Resource = {
    title: "Referrals",
    path: "/referrals",
    permission: "referral.view",
    writePermission: "referral.create",
    fields: referralFields,
    defaults: { client_id: params.get("client_id") ?? "" },
    columns: [
      { key: "source", label: "Source" },
      { key: "referral_date", label: "Referral date" },
      { key: "organization", label: "Organisation" },
      { key: "urgency", label: "Urgency" },
      { key: "status", label: "Status" },
    ],
    statusOptions: [
      "NEW",
      "SCREENING",
      "ACCEPTED",
      "DEFERRED",
      "REFERRED_ELSEWHERE",
      "DECLINED",
      "CONVERTED_TO_ADMISSION",
    ],
    actions: [
      {
        label: "Attach referral PDF",
        permission: "referral.create",
        path: (r) => `/referrals/${r.id}/documents`,
        fields: [
          {
            name: "filename",
            label: "PDF file name",
            required: true,
            default: "referral.pdf",
          },
          {
            name: "content_base64",
            label: "PDF (maximum 5 MB)",
            type: "file",
            required: true,
          },
          { name: "description", label: "Description", type: "textarea" },
        ],
      },
      {
        label: "Screen client",
        permission: "screening.create",
        path: (r) => `/referrals/${r.id}/screenings`,
        fields: screeningFields,
        visible: (r) =>
          ["NEW", "SCREENING", "DEFERRED"].includes(String(r.status)),
      },
      {
        label: "Change referral status",
        permission: "referral.update",
        path: (r) => `/referrals/${r.id}/status`,
        fields: [
          choice("status", "Status", [
            "SCREENING",
            "DEFERRED",
            "DECLINED",
            "REFERRED_ELSEWHERE",
          ]),
          reason,
        ],
      },
    ],
  };
  return (
    <>
      <PageHeader
        title="Referrals & screening"
        description="Record referral sources and clinical suitability before admission."
      />
      <ResourcePanel resource={resource} onSelect={setSelected} />
      {selected && (
        <div className="mt-4">
          <ResourcePanel
            resource={{
              title: "Referral documents",
              path: `/referrals/${selected.id}/documents`,
              permission: "referral.view",
              columns: [
                { key: "filename", label: "File" },
                { key: "version", label: "Version" },
                { key: "created_at", label: "Uploaded" },
                { key: "confidentiality", label: "Classification" },
              ],
              readLinks: [
                {
                  label: "Download PDF",
                  permission: "referral.view",
                  path: (r) => `/intake/documents/${r.id}`,
                },
              ],
            }}
          />
          <ResourcePanel
            key={selected.id}
            resource={{
              title: "Screening history",
              path: `/referrals/${selected.id}/screenings`,
              permission: "screening.view",
              columns: [
                { key: "screened_at", label: "Screened" },
                { key: "decision", label: "Decision" },
                { key: "withdrawal_risk", label: "Withdrawal risk" },
                { key: "suicide_risk", label: "Suicide risk" },
              ],
            }}
          />
        </div>
      )}
    </>
  );
}
