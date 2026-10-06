import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Form, Table } from "react-bootstrap";
import { api } from "../../api/client";
import { ErrorNotice, Pagination } from "../../components/Common";
import { todayEAT } from "../care/validation";
import type { Entity } from "../care/types";
import type { Page } from "../../types/identity";

export function ProgrammeSchedule() {
  const [start, setStart] = useState(todayEAT());
  const [end, setEnd] = useState(() =>
    new Date(Date.now() + 6 * 86400000).toISOString().slice(0, 10),
  );
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["programme-schedule", start, end, page],
    queryFn: () =>
      api<Page<Entity>>(
        `/rehabilitation/programme/schedule?from_date=${start}&to_date=${end}&page=${page}`,
      ),
  });
  return (
    <details className="card card-body mb-4">
      <summary>Daily / weekly programme schedule</summary>
      <div className="d-flex gap-3 my-3">
        <Form.Group controlId="programme-from">
          <Form.Label>From</Form.Label>
          <Form.Control
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </Form.Group>
        <Form.Group controlId="programme-to">
          <Form.Label>To (up to 93 days)</Form.Label>
          <Form.Control
            type="date"
            min={start}
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </Form.Group>
      </div>
      <ErrorNotice error={query.error} />
      <Table responsive>
        <thead>
          <tr>
            <th>Date</th>
            <th>Time (EAT)</th>
            <th>Activity</th>
            <th>Category</th>
            <th>Location</th>
          </tr>
        </thead>
        <tbody>
          {query.data?.items.map((row) => (
            <tr key={`${row.id}-${row.occurrence_date}`}>
              <td>{String(row.occurrence_date)}</td>
              <td>
                {new Date(String(row.start_at)).toLocaleTimeString("en-KE", {
                  timeZone: "Africa/Nairobi",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </td>
              <td>{String(row.title)}</td>
              <td>{String(row.category)}</td>
              <td>{String(row.location)}</td>
            </tr>
          ))}
        </tbody>
      </Table>
      <Pagination
        page={page}
        total={query.data?.meta.total ?? 0}
        onChange={setPage}
      />
    </details>
  );
}
