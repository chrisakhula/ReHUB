import { HistoryPanel } from "./HistoryPanel";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Form, Table } from "react-bootstrap";
import { api, save } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";
import {
  Empty,
  ErrorNotice,
  Loading,
  Pagination,
} from "../../components/Common";
import type { Page } from "../../types/identity";
import { RecordForm } from "./RecordForm";
import type { Action, Entity, Field, Resource, Values } from "./types";

export function readable(value: unknown): string {
  if (value === null || value === undefined || value === "")
    return "Not recorded";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "string" && /^\d{4}-\d\d-\d\dT/.test(value))
    return new Date(value).toLocaleString("en-KE", {
      timeZone: "Africa/Nairobi",
    });
  if (Array.isArray(value)) return `${value.length} entries`;
  if (typeof value === "object") return "Structured record";
  return String(value).replaceAll("_", " ");
}
function RecordValue({ value }: { value: unknown }) {
  if (Array.isArray(value))
    return (
      <ol>
        {value.map((item, i) => (
          <li key={i}>
            <RecordValue value={item} />
          </li>
        ))}
      </ol>
    );
  if (typeof value === "object" && value !== null)
    return (
      <dl className="record-detail">
        {Object.entries(value as Values).map(([key, item]) => (
          <div key={key}>
            <dt>{key.replaceAll("_", " ")}</dt>
            <dd>
              <RecordValue value={item} />
            </dd>
          </div>
        ))}
      </dl>
    );
  return <span>{readable(value)}</span>;
}
export function RecordDetails({ record }: { record: Values }) {
  return <RecordValue value={record} />;
}

export function ResourcePanel({
  resource,
  context = {},
  onSelect,
}: {
  resource: Resource;
  context?: Values;
  onSelect?: (record: Entity) => void;
}) {
  const auth = useAuth();
  const cache = useQueryClient();
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [sort, setSort] = useState(resource.sortOptions?.[0] ?? "created_at");
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<Entity | null>(null);
  const [action, setAction] = useState<Action | null>(null);
  const [success, setSuccess] = useState("");
  const canRead = auth.can(resource.permission);
  const canWrite =
    !!resource.writePermission && auth.can(resource.writePermission);
  const resolveFields = (fields: Field[], values: Values): Field[] =>
    fields.map((field) => ({
      ...field,
      source: field.source?.replace(/\{([a-z_]+)\}/g, (_, key: string) =>
        String(values[key] ?? ""),
      ),
      fields: field.fields ? resolveFields(field.fields, values) : undefined,
    }));
  const contextQuery =
    resource.clientScoped && context.client_id
      ? `&client_id=${context.client_id}`
      : resource.admissionScoped && context.admission_id
        ? `&admission_id=${context.admission_id}`
        : "";
  const query = useQuery({
    queryKey: [
      "care-records",
      resource.path,
      page,
      q,
      status,
      start,
      end,
      sort,
      contextQuery,
    ],
    queryFn: () =>
      api<Page<Entity>>(
        `${resource.path}${resource.path.includes("?") ? "&" : "?"}page=${page}&q=${encodeURIComponent(q)}&sort=${sort}${status ? `&status=${status}` : ""}${start ? `&start=${encodeURIComponent(resource.path.startsWith("/rehabilitation") ? start : new Date(`${start}T00:00:00+03:00`).toISOString())}` : ""}${end ? `&end=${encodeURIComponent(resource.path.startsWith("/rehabilitation") ? end : new Date(`${end}T23:59:59+03:00`).toISOString())}` : ""}${contextQuery}`,
      ),
    enabled: canRead,
  });
  const refreshed = async (message: string) => {
    setSuccess(message);
    setCreating(false);
    setAction(null);
    await cache.invalidateQueries();
  };
  if (!canRead)
    return (
      <Alert variant="secondary">
        Your account does not have access to {resource.title.toLowerCase()}.
      </Alert>
    );
  return (
    <section className="care-resource">
      <div className="d-flex align-items-center justify-content-between mb-3 gap-3">
        <h2>{resource.title}</h2>
        {canWrite && resource.fields && (
          <Button
            size="sm"
            disabled={
              (resource.admissionScoped && !context.admission_id) ||
              (resource.clientScoped && !context.client_id)
            }
            onClick={() => {
              setCreating(true);
              setSelected(null);
              setAction(null);
              setSuccess("");
            }}
          >
            Create record
          </Button>
        )}
      </div>
      {success && (
        <Alert variant="success" dismissible onClose={() => setSuccess("")}>
          {success}
        </Alert>
      )}
      {creating && resource.fields && (
        <div className="card card-body mb-4">
          <RecordForm
            fields={resolveFields(resource.fields, context)}
            defaults={{ ...resource.defaults, ...context }}
            onCancel={() => setCreating(false)}
            onSubmit={async (values) => {
              const scoped = {
                ...values,
                ...(resource.admissionScoped
                  ? { admission_id: context.admission_id }
                  : {}),
                ...(resource.clientScoped
                  ? { client_id: context.client_id }
                  : {}),
              };
              const record = await save<Entity>(
                resource.path,
                resource.transform ? resource.transform(scoped) : scoped,
              );
              await refreshed("Record saved.");
              setSelected(record);
              onSelect?.(record);
            }}
          />
        </div>
      )}
      <div className="card">
        <div className="card-header border-bottom-0 py-2 bg-light">
          <details>
            <summary className="fw-semibold text-secondary user-select-none" style={{ cursor: "pointer" }}>
              <i className="bi bi-funnel me-2"></i> Filters & Search
            </summary>
            <div className="table-toolbar mt-3 border-top pt-3">
              <Form.Group controlId={`${resource.title}-search`}>
                <Form.Label>Search identifiers</Form.Label>
                <Form.Control
                  value={q}
                  placeholder="Search records"
                  onChange={(e) => {
                    setQ(e.target.value);
                    setPage(1);
                  }}
                />
              </Form.Group>
              {resource.statusOptions && (
                <Form.Group controlId={`${resource.title}-status`}>
                  <Form.Label>Status</Form.Label>
                  <Form.Select
                    value={status}
                    onChange={(e) => {
                      setStatus(e.target.value);
                      setPage(1);
                    }}
                  >
                    <option value="">All statuses</option>
                    {resource.statusOptions.map((s) => (
                      <option key={s} value={s}>
                        {s.replaceAll("_", " ")}
                      </option>
                    ))}
                  </Form.Select>
                </Form.Group>
              )}
              <Form.Group controlId={`${resource.title}-sort`}>
                <Form.Label>Sort</Form.Label>
                <Form.Select
                  value={sort}
                  onChange={(e) => {
                    setSort(e.target.value);
                    setPage(1);
                  }}
                >
                  {(resource.sortOptions ?? ["created_at", "updated_at"]).map(
                    (s) => (
                      <option key={s} value={s}>
                        {s.replaceAll("_", " ")}
                      </option>
                    ),
                  )}
                </Form.Select>
              </Form.Group>
              <Form.Group controlId={`${resource.title}-start`}>
                <Form.Label>From</Form.Label>
                <Form.Control
                  type="date"
                  value={start}
                  onChange={(e) => {
                    setStart(e.target.value);
                    setPage(1);
                  }}
                />
              </Form.Group>
              <Form.Group controlId={`${resource.title}-end`}>
                <Form.Label>To</Form.Label>
                <Form.Control
                  type="date"
                  min={start}
                  value={end}
                  onChange={(e) => {
                    setEnd(e.target.value);
                    setPage(1);
                  }}
                />
              </Form.Group>
            </div>
          </details>
        </div>
        <ErrorNotice error={query.error} />
        {query.isPending ? (
          <Loading />
        ) : query.data?.items.length ? (
          <>
            <Table responsive hover className="mb-0 d-none d-lg-table">
              <thead>
                <tr>
                  {resource.columns.map((c) => (
                    <th key={c.key}>{c.label}</th>
                  ))}
                  <th>Record</th>
                </tr>
              </thead>
              <tbody>
                {query.data.items.map((row) => (
                  <tr key={row.id}>
                    {resource.columns.map((c) => (
                      <td key={c.key}>
                        {c.key === "status" ? (
                          <span className="status-badge inactive-status">
                            {readable(row[c.key])}
                          </span>
                        ) : (
                          readable(row[c.key])
                        )}
                      </td>
                    ))}
                    <td>
                      <Button
                        size="sm"
                        variant="outline-secondary"
                        onClick={() => {
                          setSelected(row);
                          setAction(null);
                          onSelect?.(row);
                        }}
                      >
                        Open
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
            <div className="list-group list-group-flush d-lg-none">
              {query.data.items.map((row) => (
                <div key={row.id} className="list-group-item py-3">
                  <div className="d-flex justify-content-between align-items-center mb-2">
                    <span className="fw-semibold">{readable(row[resource.columns[0]?.key])}</span>
                    {resource.columns.find(c => c.key === "status") && (
                      <span className="badge bg-light text-dark border">
                        {readable(row["status"])}
                      </span>
                    )}
                  </div>
                  <dl className="mb-2 row small text-secondary">
                    {resource.columns.slice(1).filter(c => c.key !== "status").map(c => (
                      <div key={c.key} className="col-6 mb-1">
                        <dt className="fw-normal text-muted mb-0">{c.label}</dt>
                        <dd className="mb-0 text-truncate">{readable(row[c.key])}</dd>
                      </div>
                    ))}
                  </dl>
                  <Button
                    size="sm"
                    variant="outline-primary"
                    className="w-100 mt-2"
                    onClick={() => {
                      setSelected(row);
                      setAction(null);
                      onSelect?.(row);
                    }}
                  >
                    Open record
                  </Button>
                </div>
              ))}
            </div>
          </>
        ) : (
          !query.error && (
            <Empty>
              No records found. Create a record when authorised, or adjust the filters.
            </Empty>
          )
        )}
        <Pagination
          page={page}
          total={query.data?.meta.total ?? 0}
          onChange={setPage}
        />
      </div>
      {selected && (
        <div className="card mt-4">
          <div className="card-header">
            <h2>Record details</h2>
            <Button
              size="sm"
              variant="outline-secondary"
              onClick={() => {
                setSelected(null);
                setAction(null);
              }}
            >
              Close details
            </Button>
          </div>
          <div className="card-body">
            <div className="d-flex flex-wrap gap-2 mb-3">
              {resource.readLinks
                ?.filter(
                  (link) =>
                    auth.can(link.permission) &&
                    (!link.visible || link.visible(selected)),
                )
                .map((link) => (
                  <a
                    className="btn btn-sm btn-outline-secondary"
                    key={link.label}
                    href={`/api/v1${link.path(selected)}`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {link.label}
                  </a>
                ))}
              {resource.actions
                ?.filter(
                  (a) =>
                    auth.can(a.permission) &&
                    (!a.visible || a.visible(selected)),
                )
                .map((a) => (
                  <Button
                    key={a.label}
                    size="sm"
                    variant="outline-primary"
                    onClick={() => setAction(a)}
                  >
                    {a.label}
                  </Button>
                ))}
            </div>
            {action ? (
              <RecordForm
                key={`${selected.id}-${action.label}`}
                fields={resolveFields(action.fields, {
                  ...context,
                  ...selected,
                })}
                defaults={{
                  ...context,
                  ...selected,
                  reason: "",
                  correction_reason: "",
                  ...action.defaults?.(selected),
                }}
                onCancel={() => setAction(null)}
                submitLabel={action.label}
                onSubmit={async (values) => {
                  const scoped = {
                    ...values,
                    ...Object.fromEntries(
                      (action.contextKeys ?? []).map((k) => [
                        k,
                        selected?.[k] ?? context[k],
                      ]),
                    ),
                  };
                  await save(
                    action.path(selected!),
                    scoped,
                    action.method ?? "POST",
                  );
                  await refreshed("Action completed.");
                  setSelected(null);
                }}
              />
            ) : (
              <RecordDetails record={selected} />
            )}
            {resource.historyPath && (
              <HistoryPanel path={resource.historyPath(selected)} />
            )}
          </div>
        </div>
      )}
    </section>
  );
}
