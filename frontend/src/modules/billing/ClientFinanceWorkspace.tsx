import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";

interface ClientAccountSummary {
  client_id: string;
  client_name: string;
  client_reference: string;
  admission_id?: string;
  admission_number?: string;
  programme?: string;
  total_charges: string;
  total_credits: string;
  total_payments: string;
  total_refunds: string;
  total_writeoffs: string;
  outstanding_balance: string;
  credit_balance: string;
  overdue_amount: string;
  active_payment_plan_id?: string;
  active_payment_plan_status?: string;
  financial_clearance_status?: string;
}

interface ClientStatementTransaction {
  date: string;
  reference: string;
  type: string;
  description: string;
  debit: number;
  credit: number;
  running_balance: number;
}

interface ClientStatementResponse {
  summary: ClientAccountSummary;
  transactions: ClientStatementTransaction[];
}

interface ClientOption {
  id: string;
  client_number: string;
  first_name: string;
  surname: string;
}

export function ClientFinanceWorkspace() {
  const auth = useAuth();
  const [selectedClientId, setSelectedClientId] = useState<string>("");
  const [docType, setDocType] = useState<string>("STATEMENT");
  const [exportReport, setExportReport] = useState<string>("AR_AGING");
  const [exportFormat, setExportFormat] = useState<"CSV" | "XLSX">("CSV");
  const [isExporting, setIsExporting] = useState<boolean>(false);

  // Fetch client list for selector
  const clientsQuery = useQuery<any>({
    queryKey: ["clients-lookup"],
    queryFn: () => api<any>("/clients"),
  });

  const clients: ClientOption[] = Array.isArray(clientsQuery.data)
    ? clientsQuery.data
    : Array.isArray(clientsQuery.data?.items)
    ? clientsQuery.data.items
    : [];

  // Fetch statement when client selected
  const statementQuery = useQuery<ClientStatementResponse>({
    queryKey: ["client-statement", selectedClientId],
    queryFn: () => api<ClientStatementResponse>(`/billing/clients/${selectedClientId}/statement`),
    enabled: Boolean(selectedClientId),
  });

  const statement = statementQuery.data;
  const summary = statement?.summary;

  const handleDownloadPdf = () => {
    if (!selectedClientId) return;
    const url = `/api/v1/billing/documents/pdf?document_type=${docType}&reference_id=${selectedClientId}`;
    window.open(url, "_blank");
  };

  const handlePrint = () => {
    window.print();
  };

  const handleExportSpreadsheet = async () => {
    try {
      setIsExporting(true);
      const url = `/api/v1/billing/exports/spreadsheet?report_type=${exportReport}&export_format=${exportFormat}`;
      window.open(url, "_blank");
    } finally {
      setIsExporting(false);
    }
  };

  const formatKes = (val: string | number | undefined) => {
    if (val === undefined || val === null) return "KES 0.00";
    const num = typeof val === "number" ? val : parseFloat(val);
    return isNaN(num) ? "KES 0.00" : `KES ${num.toLocaleString("en-KE", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="client-finance-workspace p-3">
      {/* Header & Controls Panel */}
      <div className="card shadow-sm border-0 mb-4 bg-light">
        <div className="card-body">
          <div className="row g-3 align-items-center">
            <div className="col-md-5">
              <label className="form-label fw-bold text-secondary mb-1">Select Client Account</label>
              <select
                className="form-select form-select-lg"
                value={selectedClientId}
                onChange={(e) => setSelectedClientId(e.target.value)}
              >
                <option value="">-- Choose a Client to View Financial Account --</option>
                {clients.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.client_number} — {c.first_name} {c.surname}
                  </option>
                ))}
              </select>
            </div>

            <div className="col-md-7 text-md-end pt-md-4">
              <div className="btn-group me-2" role="group">
                <select
                  className="form-select d-inline-block w-auto me-2"
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  disabled={!selectedClientId}
                >
                  <option value="STATEMENT">Account Statement PDF</option>
                  <option value="INVOICE">Current Invoice PDF</option>
                  <option value="RECEIPT">Payment Receipt PDF</option>
                  <option value="DISCHARGE_CLEARANCE">Discharge Clearance PDF</option>
                </select>
                <button
                  className="btn btn-outline-primary"
                  onClick={handleDownloadPdf}
                  disabled={!selectedClientId}
                  title="Generate Official Branded PDF"
                >
                  <i className="bi bi-file-earmark-pdf me-1"></i> Download PDF
                </button>
                <button
                  className="btn btn-outline-secondary"
                  onClick={handlePrint}
                  disabled={!selectedClientId}
                  title="Print Statement (Hides UI Controls)"
                >
                  <i className="bi bi-printer me-1"></i> Print
                </button>
              </div>

              {/* Structured Exports */}
              {auth.can("billing.export") && (
                <div className="btn-group ms-2" role="group">
                  <select
                    className="form-select d-inline-block w-auto me-1"
                    value={exportReport}
                    onChange={(e) => setExportReport(e.target.value)}
                  >
                    <option value="AR_AGING">AR Aging Report</option>
                    <option value="DAILY_COLLECTIONS">Daily Collections</option>
                    <option value="CLIENT_BALANCES">Client Balances</option>
                    <option value="RESIDENT_FUNDS">Resident Funds Subledger</option>
                    <option value="SPONSOR_BALANCES">Sponsor Balances</option>
                    <option value="REFUNDS">Refunds Register</option>
                  </select>
                  <select
                    className="form-select d-inline-block w-auto me-1"
                    value={exportFormat}
                    onChange={(e) => setExportFormat(e.target.value as "CSV" | "XLSX")}
                  >
                    <option value="CSV">CSV</option>
                    <option value="XLSX">Excel (.xlsx)</option>
                  </select>
                  <button
                    className="btn btn-success"
                    onClick={handleExportSpreadsheet}
                    disabled={isExporting}
                    title="Export Filtered Dataset to Spreadsheet"
                  >
                    <i className="bi bi-download me-1"></i> Export
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {statementQuery.isLoading && (
        <div className="text-center p-5 text-muted">
          <div className="spinner-border text-primary mb-3" role="status"></div>
          <p>Loading canonical financial ledger and transaction subledger...</p>
        </div>
      )}

      {selectedClientId && summary && (
        <div className="document-preview-container">
          {/* Official Printable Header */}
          <div className="d-flex justify-content-between align-items-center mb-4 border-bottom pb-3">
            <div>
              <h4 className="fw-bold text-primary mb-1">ARMS REHUB REHABILITATION CENTRE</h4>
              <p className="text-muted small mb-0">Confidential Client Financial Subledger & Statement</p>
              <div className="mt-2">
                <span className="badge bg-primary me-2">{summary.client_reference}</span>
                <strong className="fs-5">{summary.client_name}</strong>
                {summary.admission_number && (
                  <span className="text-muted ms-2">| Admission: {summary.admission_number} ({summary.programme})</span>
                )}
              </div>
            </div>
            <div className="text-end">
              <span className={`badge px-3 py-2 fs-6 mb-1 ${
                summary.financial_clearance_status === "CLEARED" ? "bg-success" :
                summary.financial_clearance_status === "PAYMENT_PLAN" ? "bg-info text-dark" :
                summary.financial_clearance_status === "AUTHORIZED_EXCEPTION" ? "bg-warning text-dark" : "bg-secondary"
              }`}>
                Clearance: {summary.financial_clearance_status || "NOT_REVIEWED"}
              </span>
              {summary.active_payment_plan_status && (
                <div>
                  <span className="badge bg-outline-info text-primary border border-primary">
                    Payment Plan: {summary.active_payment_plan_status}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Metric KPI Cards */}
          <div className="row g-3 mb-4">
            <div className="col-md-2">
              <div className="card border-0 shadow-sm p-3 text-center bg-white border-start border-4 border-primary">
                <div className="text-muted small fw-bold">TOTAL CHARGES</div>
                <div className="fs-5 fw-bold text-dark mt-1">{formatKes(summary.total_charges)}</div>
              </div>
            </div>
            <div className="col-md-2">
              <div className="card border-0 shadow-sm p-3 text-center bg-white border-start border-4 border-info">
                <div className="text-muted small fw-bold">CREDITS & WAIVERS</div>
                <div className="fs-5 fw-bold text-info mt-1">{formatKes(summary.total_credits)}</div>
              </div>
            </div>
            <div className="col-md-2">
              <div className="card border-0 shadow-sm p-3 text-center bg-white border-start border-4 border-success">
                <div className="text-muted small fw-bold">PAYMENTS RECEIVED</div>
                <div className="fs-5 fw-bold text-success mt-1">{formatKes(summary.total_payments)}</div>
              </div>
            </div>
            <div className="col-md-2">
              <div className="card border-0 shadow-sm p-3 text-center bg-white border-start border-4 border-secondary">
                <div className="text-muted small fw-bold">REFUNDS PROCESSED</div>
                <div className="fs-5 fw-bold text-secondary mt-1">{formatKes(summary.total_refunds)}</div>
              </div>
            </div>
            <div className="col-md-2">
              <div className="card border-0 shadow-sm p-3 text-center bg-white border-start border-4 border-danger">
                <div className="text-muted small fw-bold">OUTSTANDING DUE</div>
                <div className="fs-5 fw-bold text-danger mt-1">{formatKes(summary.outstanding_balance)}</div>
              </div>
            </div>
            <div className="col-md-2">
              <div className="card border-0 shadow-sm p-3 text-center bg-white border-start border-4 border-warning">
                <div className="text-muted small fw-bold">OVERDUE AMOUNT</div>
                <div className="fs-5 fw-bold text-warning mt-1">{formatKes(summary.overdue_amount)}</div>
              </div>
            </div>
          </div>

          {/* Chronological Transactions Table */}
          <div className="card border-0 shadow-sm mb-4">
            <div className="card-header bg-white py-3">
              <h5 className="mb-0 fw-bold text-secondary">
                <i className="bi bi-clock-history me-2"></i> Account Subledger History
              </h5>
            </div>
            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light text-uppercase small">
                  <tr>
                    <th>Date</th>
                    <th>Reference</th>
                    <th>Type</th>
                    <th>Description</th>
                    <th className="text-end">Debit (KES)</th>
                    <th className="text-end">Credit (KES)</th>
                    <th className="text-end">Running Balance (KES)</th>
                  </tr>
                </thead>
                <tbody>
                  {statement.transactions && statement.transactions.length > 0 ? (
                    statement.transactions.map((tx, idx) => (
                      <tr key={idx}>
                        <td className="text-nowrap">{tx.date}</td>
                        <td className="fw-bold">{tx.reference}</td>
                        <td>
                          <span className={`badge ${
                            tx.type === "INVOICE" ? "bg-primary" :
                            tx.type === "PAYMENT" ? "bg-success" :
                            tx.type === "CREDIT_NOTE" ? "bg-info text-dark" : "bg-secondary"
                          }`}>
                            {tx.type}
                          </span>
                        </td>
                        <td>{tx.description}</td>
                        <td className="text-end text-danger fw-semibold">
                          {tx.debit > 0 ? tx.debit.toLocaleString("en-KE", { minimumFractionDigits: 2 }) : "-"}
                        </td>
                        <td className="text-end text-success fw-semibold">
                          {tx.credit > 0 ? tx.credit.toLocaleString("en-KE", { minimumFractionDigits: 2 }) : "-"}
                        </td>
                        <td className="text-end fw-bold">
                          {tx.running_balance.toLocaleString("en-KE", { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={7} className="text-center p-4 text-muted">
                        No financial transactions recorded for this client.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Printable Footer */}
          <div className="border-top pt-3 text-muted small d-flex justify-content-between">
            <div>Generated by ReHUB Automated Client Finance Subledger Engine</div>
            <div>Phase 26.6 Production Standard &bull; Strict Decimal Precision &bull; Double-Entry GL</div>
          </div>
        </div>
      )}

      {!selectedClientId && (
        <div className="text-center p-5 border rounded bg-white text-muted">
          <i className="bi bi-wallet2 display-3 text-secondary mb-3 d-block"></i>
          <h5>No Client Account Selected</h5>
          <p>Please select a client from the dropdown above to inspect their live financial statement, generate branded PDFs, or print official documents.</p>
        </div>
      )}
    </div>
  );
}
