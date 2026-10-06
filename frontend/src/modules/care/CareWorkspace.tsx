import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { Form, Tab, Tabs } from "react-bootstrap";
import { api } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";
import { ErrorNotice, PageHeader, Pagination } from "../../components/Common";
import { ResourcePanel } from "./ResourcePanel";
import type { CareOptions, Resource, Values } from "./types";

export function CareWorkspace({
  title,
  description,
  resources,
  children,
}: {
  title: string;
  description: string;
  resources: Resource[];
  children?: React.ReactNode;
}) {
  const auth = useAuth();
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const admissionId = params.get("admission_id") ?? "";
  const options = useQuery({
    queryKey: ["care-options", search, page, admissionId],
    queryFn: () =>
      api<CareOptions>(
        `/care/options?page=${page}&q=${encodeURIComponent(search)}${admissionId ? `&selected_id=${admissionId}` : ""}`,
      ),
  });
  const admission =
    options.data?.selected ??
    options.data?.admissions.find((a) => a.id === admissionId);
  const context: Values = {
    admission_id: admissionId,
    client_id: admission?.client_id,
    therapist_id: auth.user?.id,
    facilitator_id: auth.user?.id,
    responsible_professional_id: auth.user?.id,
    assigned_staff_id: auth.user?.id,
    case_manager_id: auth.user?.id,
    counsellor_id: auth.user?.id,
  };
  const visible = resources.filter((r) => auth.can(r.permission));
  return (
    <>
      <PageHeader title={title} description={description} />
      <section className="card card-body mb-4">
        <div className="row g-3">
          <Form.Group className="col-md-5" controlId="care-search">
            <Form.Label>Find an admission</Form.Label>
            <Form.Control
              placeholder="Client name, client number or admission number"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </Form.Group>
          <Form.Group className="col-md-7" controlId="care-admission">
            <Form.Label>Admission context</Form.Label>
            <Form.Select
              value={admissionId}
              onChange={(e) => {
                params.set("admission_id", e.target.value);
                setParams(params);
              }}
            >
              <option value="">
                All admissions (choose one to record care)
              </option>
              {admissionId && !admission && (
                <option value={admissionId}>Selected admission</option>
              )}
              {options.data?.admissions.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.client_name} · {a.admission_number} · {a.status}
                </option>
              ))}
            </Form.Select>
          </Form.Group>
        </div>
        <ErrorNotice error={options.error} />
        {(options.data?.meta.total ?? 0) > 20 && (
          <Pagination
            page={page}
            total={options.data?.meta.total ?? 0}
            onChange={setPage}
          />
        )}
      </section>

      <section className="admission-context" aria-live="polite">
        {admission ? (
          <>
            <div>
              <span className="eyebrow">Active care context</span>
              <strong>{admission.client_name}</strong>
              <span>
                {admission.client_number} · {admission.admission_number}
              </span>
            </div>
            <span className="status-badge active-status">
              {admission.status.replaceAll("_", " ")}
            </span>
          </>
        ) : (
          <div>
            <span className="eyebrow">Care context</span>
            <strong>Select an admission before recording care</strong>
            <span>
              Search by client name, client number, or admission number above.
            </span>
          </div>
        )}
      </section>

      {children && (
        <>
          <div className="d-flex align-items-center mb-3 mt-4">
            <h3 className="h5 mb-0">Current work</h3>
          </div>
          <section className="mb-4">
            {children}
          </section>
        </>
      )}

      <div className="d-flex align-items-center mb-3 mt-4">
        <h3 className="h5 mb-0">Records and documentation</h3>
      </div>
      <Tabs
        defaultActiveKey={visible[0]?.path}
        className="mb-4"
        mountOnEnter
        unmountOnExit
      >
        {visible.map((resource) => (
          <Tab
            eventKey={resource.path}
            title={resource.title}
            key={resource.path}
          >
            <ResourcePanel
              key={`${resource.path}-${admissionId}`}
              resource={resource}
              context={context}
            />
          </Tab>
        ))}
      </Tabs>
      {visible.length === 0 && (
        <p>No care modules are enabled for this account.</p>
      )}
    </>
  );
}
