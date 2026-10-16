import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Alert, Badge, Button, Form, Modal, Table } from "react-bootstrap";
import { api, save } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";
import { Empty, Loading } from "../../components/Common";

interface ApprovalItem {
  id: string;
  type: "EXPENSE" | "CASH_VARIANCE" | "CREDIT_NOTE" | "WRITE_OFF";
  reference: string;
  amount: number | string;
  requestedBy: string;
  date: string;
  reason: string;
  status: string;
  raw: Record<string, unknown>;
}

export function FinanceApprovalWorkspace() {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const [filterType, setFilterType] = useState<string>("ALL");
  const [actionItem, setActionItem] = useState<{
    item: ApprovalItem;
    action: "approve" | "reject";
  } | null>(null);
  const [actionNotes, setActionNotes] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  // Queries
  const expensesQuery = useQuery({
    queryKey: ["approvals-expenses"],
    queryFn: () => api<Record<string, unknown>[]>("/finance/expenses"),
    enabled: auth.can("finance.approve"),
  });

  const cashQuery = useQuery({
    queryKey: ["approvals-cash"],
    queryFn: () => api<Record<string, unknown>[]>("/finance/cash-reconciliations"),
    enabled: auth.can("finance.approve"),
  });

  const creditNotesQuery = useQuery({
    queryKey: ["approvals-credit-notes"],
    queryFn: () => api<Record<string, unknown>[]>("/billing/credit-notes"),
    enabled: auth.can("billing.credit_note.approve"),
  });

  const writeoffsQuery = useQuery({
    queryKey: ["approvals-writeoffs"],
    queryFn: () => api<Record<string, unknown>[]>("/billing/writeoffs"),
    enabled: auth.can("billing.writeoff.approve"),
  });

  const items: ApprovalItem[] = [];

  if (expensesQuery.data && Array.isArray(expensesQuery.data)) {
    for (const exp of expensesQuery.data) {
      if (exp.status === "DRAFT") {
        items.push({
          id: String(exp.id),
          type: "EXPENSE",
          reference: String(exp.reference || exp.id).slice(0, 16),
          amount: Number(exp.amount || 0),
          requestedBy: String(exp.paid_to || "Staff"),
          date: String(exp.expense_date || exp.created_at || "").slice(0, 10),
          reason: String(exp.description || "Expense voucher"),
          status: "DRAFT",
          raw: exp,
        });
      }
    }
  }

  if (cashQuery.data && Array.isArray(cashQuery.data)) {
    for (const cr of cashQuery.data) {
      if (cr.status === "VARIANCE_REVIEW") {
        items.push({
          id: String(cr.id),
          type: "CASH_VARIANCE",
          reference: String(cr.reference_code || cr.id).slice(0, 16),
          amount: Math.abs(Number(cr.variance || 0)),
          requestedBy: String(cr.cashier_name || "Cashier"),
          date: String(cr.period_date || cr.created_at || "").slice(0, 10),
          reason: `Cash ${Number(cr.variance || 0) < 0 ? "Shortage" : "Overage"}: ${String(cr.notes || "No notes")}`,
          status: "VARIANCE_REVIEW",
          raw: cr,
        });
      }
    }
  }

  if (creditNotesQuery.data && Array.isArray(creditNotesQuery.data)) {
    for (const cn of creditNotesQuery.data) {
      if (cn.status === "DRAFT") {
        items.push({
          id: String(cn.id),
          type: "CREDIT_NOTE",
          reference: String(cn.credit_note_number || cn.id).slice(0, 16),
          amount: Number(cn.amount || 0),
          requestedBy: String(cn.requested_by || "Billing Staff"),
          date: String(cn.created_at || "").slice(0, 10),
          reason: `${String(cn.reason_code || "")}: ${String(cn.reason || "")}`,
          status: "DRAFT",
          raw: cn,
        });
      }
    }
  }

  if (writeoffsQuery.data && Array.isArray(writeoffsQuery.data)) {
    for (const wo of writeoffsQuery.data) {
      if (wo.status === "DRAFT") {
        items.push({
          id: String(wo.id),
          type: "WRITE_OFF",
          reference: String(wo.reference_code || wo.id).slice(0, 16),
          amount: Number(wo.amount || 0),
          requestedBy: String(wo.requested_by || "Billing Staff"),
          date: String(wo.created_at || "").slice(0, 10),
          reason: String(wo.reason || "Bad debt write-off"),
          status: "DRAFT",
          raw: wo,
        });
      }
    }
  }

  const filteredItems = items.filter(
    (item) => filterType === "ALL" || item.type === filterType,
  );

  const approveMutation = useMutation({
    mutationFn: async ({
      item,
      action,
      notes,
    }: {
      item: ApprovalItem;
      action: "approve" | "reject";
      notes: string;
    }) => {
      let endpoint = "";
      let payload: Record<string, unknown> = {};

      if (item.type === "EXPENSE") {
        endpoint = `/finance/expenses/${item.id}/approve`;
      } else if (item.type === "CASH_VARIANCE") {
        endpoint =
          action === "approve"
            ? `/finance/cash-reconciliations/${item.id}/approve`
            : `/finance/cash-reconciliations/${item.id}/reject`;
        payload = action === "approve" ? { approval_notes: notes } : { review_notes: notes };
      } else if (item.type === "CREDIT_NOTE") {
        endpoint =
          action === "approve"
            ? `/billing/credit-notes/${item.id}/approve`
            : `/billing/credit-notes/${item.id}/reject`;
        payload = { approval_notes: notes };
      } else if (item.type === "WRITE_OFF") {
        endpoint =
          action === "approve"
            ? `/billing/writeoffs/${item.id}/approve`
            : `/billing/writeoffs/${item.id}/reject`;
        payload = { approval_notes: notes };
      }

      return save(endpoint, payload);
    },
    onSuccess: () => {
      setActionItem(null);
      setActionNotes("");
      setActionError(null);
      queryClient.invalidateQueries({ queryKey: ["approvals-expenses"] });
      queryClient.invalidateQueries({ queryKey: ["approvals-cash"] });
      queryClient.invalidateQueries({ queryKey: ["approvals-credit-notes"] });
      queryClient.invalidateQueries({ queryKey: ["approvals-writeoffs"] });
      queryClient.invalidateQueries({ queryKey: ["finance-report"] });
    },
    onError: (err: unknown) => {
      setActionError(err instanceof Error ? err.message : "Approval action failed");
    },
  });

  const isLoading =
    expensesQuery.isLoading ||
    cashQuery.isLoading ||
    creditNotesQuery.isLoading ||
    writeoffsQuery.isLoading;

  return (
    <section className="card">
      <div className="card-header d-flex justify-content-between align-items-center">
        <div>
          <h2>Finance Approval Workspace</h2>
          <small className="text-secondary">
            Operational queue for expenses, cash variances, credit notes, and bad debt write-offs.
          </small>
        </div>
        <div className="d-flex gap-2">
          <Form.Select
            size="sm"
            style={{ width: "200px" }}
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
          >
            <option value="ALL">All Approval Types ({items.length})</option>
            <option value="EXPENSE">Expense Vouchers</option>
            <option value="CASH_VARIANCE">Cash Variances</option>
            <option value="CREDIT_NOTE">Credit Notes</option>
            <option value="WRITE_OFF">Write-Offs</option>
          </Form.Select>
        </div>
      </div>

      <div className="card-body p-0">
        {isLoading && <Loading />}

        {!isLoading && filteredItems.length === 0 ? (
          <div className="p-4">
            <Empty>No items currently require approval in this queue.</Empty>
          </div>
        ) : (
          <Table responsive hover className="mb-0 align-middle">
            <thead className="table-light">
              <tr>
                <th>Reference</th>
                <th>Type</th>
                <th>Amount (KES)</th>
                <th>Requested By</th>
                <th>Date</th>
                <th>Reason / Description</th>
                <th>Status</th>
                <th className="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item) => (
                <tr key={`${item.type}-${item.id}`}>
                  <td className="fw-medium font-monospace">{item.reference}</td>
                  <td>
                    <Badge
                      bg={
                        item.type === "EXPENSE"
                          ? "primary"
                          : item.type === "CASH_VARIANCE"
                            ? "warning"
                            : item.type === "CREDIT_NOTE"
                              ? "info"
                              : "danger"
                      }
                    >
                      {item.type.replace("_", " ")}
                    </Badge>
                  </td>
                  <td className="font-monospace">
                    {new Intl.NumberFormat("en-KE", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    }).format(Number(item.amount))}
                  </td>
                  <td>{item.requestedBy}</td>
                  <td>{item.date}</td>
                  <td className="text-truncate" style={{ maxWidth: "260px" }} title={item.reason}>
                    {item.reason}
                  </td>
                  <td>
                    <Badge bg="secondary">{item.status.replace("_", " ")}</Badge>
                  </td>
                  <td className="text-end">
                    <div className="btn-group btn-group-sm">
                      <Button
                        variant="outline-success"
                        size="sm"
                        onClick={() => {
                          setActionItem({ item, action: "approve" });
                          setActionNotes("");
                          setActionError(null);
                        }}
                      >
                        Approve
                      </Button>
                      {item.type !== "EXPENSE" && (
                        <Button
                          variant="outline-danger"
                          size="sm"
                          onClick={() => {
                            setActionItem({ item, action: "reject" });
                            setActionNotes("");
                            setActionError(null);
                          }}
                        >
                          Reject
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      {actionItem && (
        <Modal
          show={true}
          onHide={() => setActionItem(null)}
          backdrop="static"
          centered
        >
          <Modal.Header closeButton>
            <Modal.Title>
              {actionItem.action === "approve" ? "Confirm Approval" : "Confirm Rejection"} —{" "}
              {actionItem.item.type.replace("_", " ")} ({actionItem.item.reference})
            </Modal.Title>
          </Modal.Header>
          <Modal.Body>
            {actionError && <Alert variant="danger">{actionError}</Alert>}
            <p className="mb-2">
              <strong>Amount:</strong> KES{" "}
              {new Intl.NumberFormat("en-KE", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              }).format(Number(actionItem.item.amount))}
            </p>
            <p className="mb-3 text-muted">{actionItem.item.reason}</p>

            <Form.Group controlId="approval-notes">
              <Form.Label>
                {actionItem.action === "approve"
                  ? "Approval Notes / Comments"
                  : "Rejection Reason (Required)"}
              </Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                value={actionNotes}
                onChange={(e) => setActionNotes(e.target.value)}
                placeholder={
                  actionItem.action === "approve"
                    ? "Optional approval remarks..."
                    : "Specify the reason for rejecting this transaction..."
                }
                required={actionItem.action === "reject"}
              />
            </Form.Group>
          </Modal.Body>
          <Modal.Footer>
            <Button
              variant="outline-secondary"
              onClick={() => setActionItem(null)}
              disabled={approveMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant={actionItem.action === "approve" ? "success" : "danger"}
              disabled={
                approveMutation.isPending ||
                (actionItem.action === "reject" && !actionNotes.trim())
              }
              onClick={() => {
                approveMutation.mutate({
                  item: actionItem.item,
                  action: actionItem.action,
                  notes: actionNotes.trim(),
                });
              }}
            >
              {approveMutation.isPending
                ? "Processing..."
                : actionItem.action === "approve"
                  ? "Confirm & Post GL"
                  : "Reject Transaction"}
            </Button>
          </Modal.Footer>
        </Modal>
      )}
    </section>
  );
}
