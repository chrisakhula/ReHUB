import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Alert, Badge, Button, Form, Table } from "react-bootstrap";
import { api } from "../../api/client";
import { Empty, ErrorNotice, Loading } from "../../components/Common";

interface IntegrityItem {
  invoice_id: string;
  invoice_number: string;
  billing_amount: number | string;
  gl_amount: number | string;
  difference: number | string;
  status: "MATCHED" | "MISMATCH" | "MISSING_JOURNAL" | "DUPLICATE_JOURNAL";
  details: string | null;
}

interface IntegrityReport {
  total_checked: number;
  matched_count: number;
  mismatch_count: number;
  missing_journal_count: number;
  duplicate_journal_count: number;
  items: IntegrityItem[];
}

function formatKES(val: number | string): string {
  return new Intl.NumberFormat("en-KE", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(val));
}

export function FinanceIntegrityPanel() {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const query = useQuery<IntegrityReport>({
    queryKey: ["finance-billing-gl-integrity"],
    queryFn: () => api<IntegrityReport>("/finance/integrity/billing-gl"),
  });

  const report = query.data;
  const items = report?.items || [];
  const filteredItems = items.filter(
    (item) => statusFilter === "ALL" || item.status === statusFilter,
  );

  return (
    <section className="card">
      <div className="card-header d-flex justify-content-between align-items-center">
        <div>
          <h2>Billing-to-GL Integrity Diagnostic</h2>
          <small className="text-secondary">
            Operational reconciliation between Patient Invoices and General Ledger Accounts Receivable entries.
          </small>
        </div>
        <div className="d-flex gap-2">
          <Button
            size="sm"
            variant="outline-primary"
            onClick={() => query.refetch()}
            disabled={query.isFetching}
          >
            {query.isFetching ? "Scanning..." : "Re-scan Ledger"}
          </Button>
        </div>
      </div>

      <div className="card-body">
        <Alert variant="info" className="d-flex align-items-start gap-2 mb-3">
          <i className="bi bi-shield-check fs-5" />
          <div className="small">
            <strong>Non-Destructive Diagnostic:</strong> This service detects historical or runtime
            divergences between billing invoice totals and corresponding General Ledger postings.
            Identified exceptions are never auto-repaired and must be reviewed by authorized finance personnel.
          </div>
        </Alert>

        {query.isLoading && <Loading />}
        <ErrorNotice error={query.error} />

        {report && (
          <>
            <div className="row g-3 mb-4">
              <div className="col-md">
                <div className="border rounded p-3 text-center bg-light">
                  <div className="text-muted small">Total Invoices Checked</div>
                  <div className="fs-4 fw-bold">{report.total_checked}</div>
                </div>
              </div>
              <div className="col-md">
                <div className="border rounded p-3 text-center bg-light text-success">
                  <div className="text-muted small">Matched Journals</div>
                  <div className="fs-4 fw-bold">{report.matched_count}</div>
                </div>
              </div>
              <div className="col-md">
                <div className="border rounded p-3 text-center bg-light text-danger">
                  <div className="text-muted small">Amount Mismatches</div>
                  <div className="fs-4 fw-bold">{report.mismatch_count}</div>
                </div>
              </div>
              <div className="col-md">
                <div className="border rounded p-3 text-center bg-light text-warning">
                  <div className="text-muted small">Missing Journals</div>
                  <div className="fs-4 fw-bold">{report.missing_journal_count}</div>
                </div>
              </div>
              <div className="col-md">
                <div className="border rounded p-3 text-center bg-light text-secondary">
                  <div className="text-muted small">Duplicate Journals</div>
                  <div className="fs-4 fw-bold">{report.duplicate_journal_count}</div>
                </div>
              </div>
            </div>

            <div className="d-flex justify-content-between align-items-center mb-3">
              <h5 className="mb-0">Diagnostic Details</h5>
              <div className="d-flex align-items-center gap-2">
                <Form.Label htmlFor="status-filter" className="small text-muted mb-0">
                  Filter:
                </Form.Label>
                <Form.Select
                  id="status-filter"
                  size="sm"
                  style={{ width: "220px" }}
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <option value="ALL">All Statuses ({items.length})</option>
                  <option value="MATCHED">MATCHED ({report.matched_count})</option>
                  <option value="MISMATCH">MISMATCH ({report.mismatch_count})</option>
                  <option value="MISSING_JOURNAL">MISSING JOURNAL ({report.missing_journal_count})</option>
                  <option value="DUPLICATE_JOURNAL">DUPLICATE JOURNAL ({report.duplicate_journal_count})</option>
                </Form.Select>
              </div>
            </div>

            {filteredItems.length === 0 ? (
              <Empty>No items match the selected integrity filter.</Empty>
            ) : (
              <Table responsive hover className="mb-0 align-middle">
                <thead className="table-light">
                  <tr>
                    <th>Invoice Reference</th>
                    <th className="text-end">Billing Amount</th>
                    <th className="text-end">GL Amount</th>
                    <th className="text-end">Difference</th>
                    <th className="text-center">Integrity Status</th>
                    <th>Audit Details</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredItems.map((item) => (
                    <tr key={item.invoice_id}>
                      <td className="font-monospace fw-medium">{item.invoice_number}</td>
                      <td className="text-end font-monospace">{formatKES(item.billing_amount)}</td>
                      <td className="text-end font-monospace">{formatKES(item.gl_amount)}</td>
                      <td
                        className={`text-end font-monospace ${
                          Number(item.difference) !== 0 ? "text-danger fw-bold" : "text-muted"
                        }`}
                      >
                        {formatKES(item.difference)}
                      </td>
                      <td className="text-center">
                        <Badge
                          bg={
                            item.status === "MATCHED"
                              ? "success"
                              : item.status === "MISMATCH"
                                ? "danger"
                                : item.status === "MISSING_JOURNAL"
                                  ? "warning"
                                  : "secondary"
                          }
                        >
                          {item.status.replace("_", " ")}
                        </Badge>
                      </td>
                      <td className="small text-muted">{item.details || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            )}
          </>
        )}
      </div>
    </section>
  );
}
