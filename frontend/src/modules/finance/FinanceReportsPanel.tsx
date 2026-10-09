import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button, Form, Table } from "react-bootstrap";
import { api } from "../../api/client";
import { Empty, ErrorNotice, Loading } from "../../components/Common";

const reports = [
  { id: "trial-balance", label: "Trial Balance" },
  { id: "profit-and-loss", label: "Profit & Loss" },
  { id: "balance-sheet", label: "Balance Sheet" },
  { id: "general-ledger", label: "General Ledger" },
];

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not recorded";
  if (typeof value === "number") {
    return new Intl.NumberFormat("en-KE", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  }
  return String(value).replaceAll("_", " ");
}

function Rows({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows.length) return <Empty>No report rows for the selected period.</Empty>;
  const columns = Object.keys(rows[0]).filter((key) => key !== "id" && key !== "lines");
  return (
    <Table responsive hover className="mb-0">
      <thead>
        <tr>
          {columns.map((column) => (
            <th key={column}>{column.replaceAll("_", " ")}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={String(row.id ?? index)}>
            {columns.map((column) => (
              <td key={column}>{display(row[column])}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

export function FinanceReportsPanel() {
  const [report, setReport] = useState("trial-balance");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const query = new URLSearchParams();
  if (report === "balance-sheet") {
    if (end) query.set("as_of", end);
  } else {
    if (start) query.set("start", start);
    if (end) query.set("end", end);
  }
  const result = useQuery({
    queryKey: ["finance-report", report, start, end],
    queryFn: () => api<Record<string, unknown>>(`/finance/reports/${report}?${query}`),
  });
  const data = result.data;
  const selected = reports.find((item) => item.id === report);
  const rows =
    report === "profit-and-loss"
      ? [
          ...((data?.income as Record<string, unknown>[] | undefined) ?? []),
          ...((data?.cogs as Record<string, unknown>[] | undefined) ?? []),
          ...((data?.expenses as Record<string, unknown>[] | undefined) ?? []),
        ]
      : report === "balance-sheet"
        ? [
            ...((data?.assets as Record<string, unknown>[] | undefined) ?? []),
            ...((data?.liabilities as Record<string, unknown>[] | undefined) ?? []),
            ...((data?.equity as Record<string, unknown>[] | undefined) ?? []),
          ]
        : ((data?.items as Record<string, unknown>[] | undefined) ?? []);

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <h2>Finance reports</h2>
          <small className="text-secondary">Ledger-backed reports for review and export checks.</small>
        </div>
      </div>
      <div className="card-body">
        <div className="table-toolbar p-0 pb-3 border-bottom mb-3">
          <Form.Group controlId="finance-report-type">
            <Form.Label>Report</Form.Label>
            <Form.Select value={report} onChange={(event) => setReport(event.target.value)}>
              {reports.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.label}
                </option>
              ))}
            </Form.Select>
          </Form.Group>
          <Form.Group controlId="finance-report-start">
            <Form.Label>From</Form.Label>
            <Form.Control
              type="date"
              value={start}
              disabled={report === "balance-sheet"}
              onChange={(event) => setStart(event.target.value)}
            />
          </Form.Group>
          <Form.Group controlId="finance-report-end">
            <Form.Label>{report === "balance-sheet" ? "As of" : "To"}</Form.Label>
            <Form.Control type="date" value={end} onChange={(event) => setEnd(event.target.value)} />
          </Form.Group>
          <div className="d-flex align-items-end">
            <Button variant="outline-secondary" onClick={() => result.refetch()}>
              Refresh
            </Button>
          </div>
        </div>
        <ErrorNotice error={result.error} />
        {result.isPending ? (
          <Loading />
        ) : (
          <>
            <div className="d-flex justify-content-between align-items-center mb-3">
              <h3 className="h6 mb-0">{selected?.label}</h3>
              {Boolean(data?.totals) && (
                <span className="text-secondary small">Totals included below</span>
              )}
            </div>
            <Rows rows={rows} />
            {data?.totals ? (
              <dl className="record-detail mt-3">
                {Object.entries(data.totals as Record<string, unknown>).map(([key, value]) => (
                  <div key={key}>
                    <dt>{key.replaceAll("_", " ")}</dt>
                    <dd>{display(value)}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
          </>
        )}
      </div>
    </section>
  );
}
