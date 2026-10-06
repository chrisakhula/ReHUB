import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Form, Table } from "react-bootstrap";
import { api } from "../../api/client";
import type { AuditEvent, Page } from "../../types/identity";
import {
  Empty,
  ErrorNotice,
  Loading,
  PageHeader,
  Pagination,
} from "../../components/Common";

export function AuditPage() {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const query = useQuery({
    queryKey: ["audit", page, q, start, end],
    queryFn: () =>
      api<Page<AuditEvent>>(
        `/audit?page=${page}&q=${encodeURIComponent(q)}${start ? `&start=${encodeURIComponent(new Date(`${start}T00:00:00+03:00`).toISOString())}` : ""}${end ? `&end=${encodeURIComponent(new Date(`${end}T23:59:59+03:00`).toISOString())}` : ""}`,
      ),
  });
  return (
    <>
      <PageHeader
        title="Audit trail"
        description="An attributable, append-only history of security and administration activity."
      />
      <section className="card">
        <div className="table-toolbar">
          <Form.Group controlId="audit-search">
            <Form.Label>Search action</Form.Label>
            <Form.Control
              value={q}
              placeholder="e.g. user.updated"
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
            />
          </Form.Group>
          <Form.Group controlId="audit-start">
            <Form.Label>From date (EAT)</Form.Label>
            <Form.Control
              type="date"
              value={start}
              onChange={(e) => {
                setStart(e.target.value);
                setPage(1);
              }}
            />
          </Form.Group>
          <Form.Group controlId="audit-end">
            <Form.Label>To date (EAT)</Form.Label>
            <Form.Control
              type="date"
              value={end}
              min={start}
              onChange={(e) => {
                setEnd(e.target.value);
                setPage(1);
              }}
            />
          </Form.Group>
        </div>
        <ErrorNotice error={query.error} />
        {query.isPending ? (
          <Loading />
        ) : query.data?.items.length ? (
          <Table responsive hover className="mb-0">
            <thead>
              <tr>
                <th>Time (EAT)</th>
                <th>Action</th>
                <th>Entity</th>
                <th>Actor / source</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {query.data.items.map((event) => (
                <tr key={event.id}>
                  <td className="text-nowrap">
                    {new Date(event.timestamp).toLocaleString("en-KE", {
                      timeZone: "Africa/Nairobi",
                    })}
                  </td>
                  <td>
                    <code>{event.action}</code>
                  </td>
                  <td>
                    {event.entity}
                    <small className="d-block text-secondary record-id">
                      {event.entity_id}
                    </small>
                  </td>
                  <td>
                    <small className="record-id">
                      {event.user_id ?? "Anonymous"}
                    </small>
                    <small className="d-block text-secondary">
                      {event.ip_address}
                    </small>
                  </td>
                  <td>
                    <details>
                      <summary>Inspect</summary>
                      <p className="small">
                        {event.reason ?? "No reason recorded"}
                      </p>
                      <pre className="audit-json">
                        {JSON.stringify(
                          {
                            previous: event.previous_values,
                            new: event.new_values,
                          },
                          null,
                          2,
                        )}
                      </pre>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          !query.error && <Empty>No audit events match these filters.</Empty>
        )}
        <Pagination
          page={page}
          total={query.data?.meta.total ?? 0}
          onChange={setPage}
        />
      </section>
    </>
  );
}
