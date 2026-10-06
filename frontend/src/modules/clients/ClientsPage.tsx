import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/Common";
import { ResourcePanel } from "../care/ResourcePanel";
import { clientFields, contactFields, reason } from "../care/fields";
import type { Entity, Resource } from "../care/types";

const registry: Resource = {
  title: "Master client registry",
  path: "/clients",
  permission: "client.view",
  writePermission: "client.create",
  fields: clientFields,
  columns: [
    { key: "client_number", label: "Client number" },
    { key: "first_name", label: "First name" },
    { key: "surname", label: "Surname" },
    { key: "phone", label: "Phone" },
    { key: "active", label: "Active" },
  ],
  sortOptions: ["created_at", "surname", "client_number"],
  readLinks: [
    {
      label: "Download client photo",
      permission: "client.view",
      path: (r) => `/intake/documents/${r.photo_reference}`,
      visible: (r) => !!r.photo_reference,
    },
  ],
  historyPath: (r) => `/clients/${r.id}/history`,
  actions: [
    {
      label: "Upload client photo",
      permission: "client.update",
      path: (r) => `/clients/${r.id}/photo`,
      fields: [
        {
          name: "filename",
          label: "File name (.jpg or .png)",
          required: true,
          default: "photo.jpg",
        },
        {
          name: "content_base64",
          label: "Client photo (maximum 3 MB)",
          type: "file",
          accept: "image/jpeg,image/png",
          required: true,
        },
      ],
    },
    {
      label: "Update demographics",
      permission: "client.update",
      path: (r) => `/clients/${r.id}`,
      method: "PUT",
      fields: [...clientFields, reason],
    },
  ],
};
export function ClientsPage() {
  const [client, setClient] = useState<Entity | null>(null);
  return (
    <>
      <PageHeader
        title="Client registry"
        description="One permanent record for every client, retained across admissions."
      />
      <ResourcePanel resource={registry} onSelect={setClient} />
      {client && (
        <section className="mt-4">
          <div className="d-flex gap-2 mb-3">
            <Link
              className="btn btn-outline-primary"
              to={`/referrals?client_id=${client.id}`}
            >
              Refer this client
            </Link>
            <Link
              className="btn btn-outline-primary"
              to={`/admissions?client_id=${client.id}`}
            >
              Admission history
            </Link>
          </div>
          <ResourcePanel
            key={client.id}
            resource={{
              title: "Client contacts",
              path: `/clients/${client.id}/contacts`,
              permission: "client.view",
              writePermission: "client.update",
              fields: contactFields,
              columns: [
                { key: "name", label: "Name" },
                { key: "kind", label: "Type" },
                { key: "relationship", label: "Relationship" },
                { key: "phone", label: "Phone" },
                { key: "authorized_contact", label: "Authorised" },
              ],
              actions: [
                {
                  label: "Update contact",
                  permission: "client.update",
                  path: (r) => `/clients/${client.id}/contacts/${r.id}`,
                  method: "PUT",
                  fields: contactFields,
                },
              ],
            }}
          />
        </section>
      )}
    </>
  );
}
