import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";

interface MpesaTransactionItem {
  id: string;
  facility_id: string;
  transaction_reference: string;
  phone_number: string;
  amount: number;
  timestamp: string | null;
  client_id: string | null;
  invoice_id: string | null;
  payer_id: string | null;
  merchant_request_id: string | null;
  checkout_request_id: string | null;
  response_code: string | null;
  customer_message: string | null;
  status: string;
  reconciliation_status: string;
  reconciled_payment_id: string | null;
  reconciled_by_id: string | null;
  reconciled_at: string | null;
  reconciliation_notes: string | null;
}

interface ReconciliationResponse {
  items: MpesaTransactionItem[];
  meta: {
    total: number;
    page: number;
    limit: number;
    pages: number;
  };
}

export function MpesaReconciliationWorkspace() {
  const auth = useAuth();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [reconFilter, setReconFilter] = useState<string>("");
  const [searchTerm, setSearchTerm] = useState<string>("");

  // STK Push Modal State
  const [showStkModal, setShowStkModal] = useState(false);
  const [stkInvoiceId, setStkInvoiceId] = useState("");
  const [stkClientId, setStkClientId] = useState("");
  const [stkPhone, setStkPhone] = useState("");
  const [stkAmount, setStkAmount] = useState("");
  const [stkMessage, setStkMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Manual Allocation Modal State
  const [allocatingTx, setAllocatingTx] = useState<MpesaTransactionItem | null>(null);
  const [allocInvoiceId, setAllocInvoiceId] = useState("");
  const [allocNotes, setAllocNotes] = useState("");
  const [allocMessage, setAllocMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Fetch transactions
  const { data, isLoading, isError, refetch } = useQuery<ReconciliationResponse>({
    queryKey: ["mpesa-reconciliation", page, statusFilter, reconFilter, searchTerm],
    queryFn: async () => {
      const params = new URLSearchParams();
      params.append("page", String(page));
      params.append("limit", "20");
      if (statusFilter) params.append("status", statusFilter);
      if (reconFilter) params.append("reconciliation_status", reconFilter);
      if (searchTerm) params.append("search", searchTerm);
      return api<ReconciliationResponse>(`/billing/mpesa/reconciliation?${params.toString()}`);
    },
  });

  // STK Push Mutation
  const stkMutation = useMutation({
    mutationFn: async (payload: { client_id: string; invoice_id: string; phone_number: string; amount: number }) => {
      return api("/billing/mpesa/stk-push", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    onSuccess: () => {
      setStkMessage({ type: "success", text: "STK Push initiated successfully! Please check client's mobile handset." });
      queryClient.invalidateQueries({ queryKey: ["mpesa-reconciliation"] });
      setTimeout(() => {
        setShowStkModal(false);
        setStkMessage(null);
        setStkInvoiceId("");
        setStkClientId("");
        setStkPhone("");
        setStkAmount("");
      }, 2500);
    },
    onError: (err: any) => {
      setStkMessage({ type: "error", text: err?.message || "Failed to initiate STK push." });
    },
  });

  // Manual Allocation Mutation
  const allocMutation = useMutation({
    mutationFn: async (payload: { transaction_id: string; invoice_id: string; notes: string }) => {
      return api(`/billing/mpesa/reconciliation/${payload.transaction_id}/allocate`, {
        method: "POST",
        body: JSON.stringify({
          invoice_id: payload.invoice_id,
          notes: payload.notes,
        }),
      });
    },
    onSuccess: () => {
      setAllocMessage({ type: "success", text: "Transaction successfully allocated and posted to General Ledger." });
      queryClient.invalidateQueries({ queryKey: ["mpesa-reconciliation"] });
      setTimeout(() => {
        setAllocatingTx(null);
        setAllocMessage(null);
        setAllocInvoiceId("");
        setAllocNotes("");
      }, 2000);
    },
    onError: (err: any) => {
      setAllocMessage({ type: "error", text: err?.message || "Manual allocation failed." });
    },
  });

  const handleInitiateStk = (e: React.FormEvent) => {
    e.preventDefault();
    if (!stkInvoiceId || !stkClientId || !stkPhone || !stkAmount) return;
    stkMutation.mutate({
      client_id: stkClientId,
      invoice_id: stkInvoiceId,
      phone_number: stkPhone,
      amount: parseFloat(stkAmount),
    });
  };

  const handleManualAllocate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!allocatingTx || !allocInvoiceId) return;
    allocMutation.mutate({
      transaction_id: allocatingTx.id,
      invoice_id: allocInvoiceId,
      notes: allocNotes,
    });
  };

  const items = data?.items || [];
  const autoReconciledCount = items.filter((t) => t.reconciliation_status === "AUTO_RECONCILED").length;
  const unmatchedCount = items.filter((t) => t.reconciliation_status === "UNMATCHED").length;
  const failedCount = items.filter((t) => t.status === "FAILED" || t.status === "CANCELLED").length;

  return (
    <div className="container-fluid py-3">
      {/* Header and Action */}
      <div className="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h2 className="h4 mb-1">M-Pesa Reconciliation & STK Push Workspace</h2>
          <p className="text-muted small mb-0">
            Real-time Daraja transaction stream, automatic GL journal balancing, and unmatched payment allocation.
          </p>
        </div>
        <div>
          {auth.can("billing.collect_payment") && (
            <button
              className="btn btn-primary btn-sm me-2"
              onClick={() => setShowStkModal(true)}
            >
              <strong>+ Trigger STK Push</strong>
            </button>
          )}
          <button className="btn btn-outline-secondary btn-sm" onClick={() => refetch()}>
            Refresh Stream
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="row g-3 mb-4">
        <div className="col-md-3">
          <div className="card shadow-sm border-0 border-start border-primary border-4 p-3">
            <span className="text-muted small">Total Transactions</span>
            <span className="h4 mb-0 mt-1">{data?.meta.total ?? 0}</span>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card shadow-sm border-0 border-start border-success border-4 p-3">
            <span className="text-muted small">Auto-Reconciled</span>
            <span className="h4 text-success mb-0 mt-1">{autoReconciledCount}</span>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card shadow-sm border-0 border-start border-warning border-4 p-3">
            <span className="text-muted small">Unmatched / In Review</span>
            <span className="h4 text-warning mb-0 mt-1">{unmatchedCount}</span>
          </div>
        </div>
        <div className="col-md-3">
          <div className="card shadow-sm border-0 border-start border-danger border-4 p-3">
            <span className="text-muted small">Failed / Cancelled</span>
            <span className="h4 text-danger mb-0 mt-1">{failedCount}</span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card shadow-sm border-0 p-3 mb-3">
        <div className="row g-2">
          <div className="col-md-4">
            <input
              type="text"
              className="form-control form-control-sm"
              placeholder="Search reference, phone, receipt..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="col-md-3">
            <select
              className="form-select form-select-sm"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="">All Statuses</option>
              <option value="SUCCESS">SUCCESS</option>
              <option value="PENDING">PENDING</option>
              <option value="FAILED">FAILED</option>
              <option value="CANCELLED">CANCELLED</option>
            </select>
          </div>
          <div className="col-md-3">
            <select
              className="form-select form-select-sm"
              value={reconFilter}
              onChange={(e) => setReconFilter(e.target.value)}
            >
              <option value="">All Reconciliation</option>
              <option value="AUTO_RECONCILED">AUTO_RECONCILED</option>
              <option value="MANUAL_REVIEW">MANUAL_REVIEW</option>
              <option value="UNMATCHED">UNMATCHED</option>
              <option value="FAILED">FAILED</option>
            </select>
          </div>
          <div className="col-md-2">
            <button
              className="btn btn-outline-dark btn-sm w-100"
              onClick={() => {
                setStatusFilter("");
                setReconFilter("");
                setSearchTerm("");
              }}
            >
              Reset Filters
            </button>
          </div>
        </div>
      </div>

      {/* Data Table */}
      <div className="card shadow-sm border-0">
        <div className="table-responsive">
          <table className="table table-hover align-middle mb-0">
            <thead className="table-light">
              <tr className="small text-muted">
                <th>Reference</th>
                <th>Phone Number</th>
                <th>Amount (KSh)</th>
                <th>Timestamp</th>
                <th>Status</th>
                <th>Reconciliation</th>
                <th>Invoice / Client</th>
                <th className="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={8} className="text-center py-4">
                    <span className="spinner-border spinner-border-sm me-2" role="status" />
                    Loading transaction records...
                  </td>
                </tr>
              )}
              {isError && (
                <tr>
                  <td colSpan={8} className="text-center py-4 text-danger">
                    Error loading reconciliation data.
                  </td>
                </tr>
              )}
              {!isLoading && items.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center py-4 text-muted">
                    No transactions found matching criteria.
                  </td>
                </tr>
              )}
              {!isLoading &&
                items.map((tx) => (
                  <tr key={tx.id} className="small">
                    <td>
                      <code className="text-dark fw-bold">{tx.transaction_reference}</code>
                      {tx.checkout_request_id && (
                        <div className="text-muted text-truncate" style={{ maxWidth: 140 }}>
                          <small>{tx.checkout_request_id}</small>
                        </div>
                      )}
                    </td>
                    <td>{tx.phone_number}</td>
                    <td>
                      <strong>{Number(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}</strong>
                    </td>
                    <td>{tx.timestamp ? new Date(tx.timestamp).toLocaleString() : "—"}</td>
                    <td>
                      <span
                        className={`badge ${
                          tx.status === "SUCCESS"
                            ? "bg-success"
                            : tx.status === "PENDING"
                            ? "bg-primary"
                            : "bg-danger"
                        }`}
                      >
                        {tx.status}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          tx.reconciliation_status === "AUTO_RECONCILED"
                            ? "bg-success text-white"
                            : tx.reconciliation_status === "MANUAL_REVIEW"
                            ? "bg-warning text-dark"
                            : tx.reconciliation_status === "UNMATCHED"
                            ? "bg-danger text-white"
                            : "bg-secondary text-white"
                        }`}
                      >
                        {tx.reconciliation_status}
                      </span>
                    </td>
                    <td>
                      {tx.invoice_id ? (
                        <div>
                          <small className="text-muted">Inv: </small>
                          <span className="font-monospace">{tx.invoice_id.substring(0, 8)}...</span>
                        </div>
                      ) : (
                        <span className="text-muted fst-italic">Unlinked</span>
                      )}
                    </td>
                    <td className="text-end">
                      {tx.reconciliation_status === "UNMATCHED" && auth.can("finance.reconcile") && (
                        <button
                          className="btn btn-outline-primary btn-sm py-0 px-2"
                          onClick={() => setAllocatingTx(tx)}
                        >
                          Allocate
                        </button>
                      )}
                      {tx.reconciliation_notes && (
                        <span
                          className="badge bg-light text-muted ms-1"
                          title={tx.reconciliation_notes}
                        >
                          Notes
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.meta.pages > 1 && (
          <div className="card-footer bg-white d-flex justify-content-between align-items-center py-2">
            <span className="text-muted small">
              Page {data.meta.page} of {data.meta.pages} ({data.meta.total} total)
            </span>
            <div className="btn-group btn-group-sm">
              <button
                className="btn btn-outline-secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </button>
              <button
                className="btn btn-outline-secondary"
                disabled={page >= data.meta.pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* STK Push Modal */}
      {showStkModal && (
        <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow">
              <div className="modal-header">
                <h5 className="modal-title h6">Trigger M-Pesa STK Push</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setShowStkModal(false)}
                />
              </div>
              <form onSubmit={handleInitiateStk}>
                <div className="modal-body">
                  {stkMessage && (
                    <div
                      className={`alert alert-${
                        stkMessage.type === "success" ? "success" : "danger"
                      } py-2 small`}
                    >
                      {stkMessage.text}
                    </div>
                  )}
                  <div className="mb-3">
                    <label className="form-label small fw-semibold">Client</label>
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      placeholder="e.g. ARS-00001 or Client ID"
                      value={stkClientId}
                      onChange={(e) => setStkClientId(e.target.value)}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label small fw-semibold">Invoice</label>
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      placeholder="e.g. INV-00001 or Invoice ID"
                      value={stkInvoiceId}
                      onChange={(e) => setStkInvoiceId(e.target.value)}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label small fw-semibold">Phone Number</label>
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      placeholder="e.g. 254712345678 or 0712345678"
                      value={stkPhone}
                      onChange={(e) => setStkPhone(e.target.value)}
                      required
                    />
                    <small className="text-muted">Must be an active Safaricom line.</small>
                  </div>
                  <div className="mb-3">
                    <label className="form-label small fw-semibold">Amount (KSh)</label>
                    <input
                      type="number"
                      step="0.01"
                      className="form-control form-control-sm"
                      placeholder="0.00"
                      value={stkAmount}
                      onChange={(e) => setStkAmount(e.target.value)}
                      required
                    />
                  </div>
                </div>
                <div className="modal-footer py-2">
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setShowStkModal(false)}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary btn-sm"
                    disabled={stkMutation.isPending}
                  >
                    {stkMutation.isPending ? "Sending Request..." : "Send STK Push Prompt"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Manual Allocation Modal */}
      {allocatingTx && (
        <div className="modal show d-block" tabIndex={-1} style={{ backgroundColor: "rgba(0,0,0,0.5)" }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow">
              <div className="modal-header">
                <h5 className="modal-title h6">Manual Payment Allocation</h5>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setAllocatingTx(null)}
                />
              </div>
              <form onSubmit={handleManualAllocate}>
                <div className="modal-body">
                  {allocMessage && (
                    <div
                      className={`alert alert-${
                        allocMessage.type === "success" ? "success" : "danger"
                      } py-2 small`}
                    >
                      {allocMessage.text}
                    </div>
                  )}
                  <div className="bg-light p-3 rounded mb-3 small">
                    <div>
                      <strong>Reference:</strong> {allocatingTx.transaction_reference}
                    </div>
                    <div>
                      <strong>Phone:</strong> {allocatingTx.phone_number}
                    </div>
                    <div>
                      <strong>Amount:</strong> KSh {Number(allocatingTx.amount).toLocaleString()}
                    </div>
                  </div>
                  <div className="mb-3">
                    <label className="form-label small fw-semibold">Target Invoice</label>
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      placeholder="Target Invoice Ref / Number (e.g. INV-00001)"
                      value={allocInvoiceId}
                      onChange={(e) => setAllocInvoiceId(e.target.value)}
                      required
                    />
                  </div>
                  <div className="mb-3">
                    <label className="form-label small fw-semibold">Audited Allocation Notes</label>
                    <textarea
                      className="form-control form-control-sm"
                      rows={3}
                      placeholder="Justification or cross-reference for finance audit..."
                      value={allocNotes}
                      onChange={(e) => setAllocNotes(e.target.value)}
                    />
                  </div>
                </div>
                <div className="modal-footer py-2">
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setAllocatingTx(null)}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-success btn-sm"
                    disabled={allocMutation.isPending}
                  >
                    {allocMutation.isPending ? "Allocating..." : "Confirm & Post to GL"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
