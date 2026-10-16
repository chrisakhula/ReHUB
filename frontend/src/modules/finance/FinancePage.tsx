import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Tab, Tabs } from "react-bootstrap";
import { save } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";
import { ErrorNotice, PageHeader } from "../../components/Common";
import { ResourcePanel } from "../care/ResourcePanel";
import { FinanceReportsPanel } from "./FinanceReportsPanel";
import { FinanceApprovalWorkspace } from "./FinanceApprovalWorkspace";
import { FinanceIntegrityPanel } from "./FinanceIntegrityPanel";
import { financeResources } from "./resources";

export function FinancePage() {
  const auth = useAuth();
  const cache = useQueryClient();
  const seed = useMutation({
    mutationFn: () => save("/finance/seed", {}),
    onSuccess: () => cache.invalidateQueries(),
  });
  const visible = financeResources.filter((resource) => auth.can(resource.permission));
  const canApprove =
    auth.can("finance.approve") ||
    auth.can("billing.credit_note.approve") ||
    auth.can("billing.writeoff.approve");
  const canAudit = auth.can("finance.audit");

  return (
    <>
      <PageHeader
        title="Finance ledger"
        description="Manage chart of accounts, period controls, journals, payables, expenses and reconciliations."
      />
      <section className="phase-notice">
        <i className="bi bi-bank" aria-hidden="true" />
        <div>
          <strong>Controlled ledger foundation</strong>
          <p>
            Finance records post into balanced journals, with fiscal-period checks and approval
            controls for sensitive actions.
          </p>
        </div>
        {auth.can("finance.configure") && (
          <Button
            size="sm"
            variant="outline-primary"
            disabled={seed.isPending}
            onClick={() => seed.mutate()}
          >
            {seed.isPending ? "Seeding..." : "Seed defaults"}
          </Button>
        )}
      </section>
      <ErrorNotice error={seed.error} />
      {seed.isSuccess && (
        <Alert variant="success" dismissible>
          Finance defaults checked and seeded where needed.
        </Alert>
      )}
      <Tabs defaultActiveKey={canApprove ? "approvals" : (visible[0]?.path ?? "reports")} className="mb-4" mountOnEnter unmountOnExit>
        {canApprove && (
          <Tab eventKey="approvals" title="Approval Queue">
            <FinanceApprovalWorkspace />
          </Tab>
        )}
        {visible.map((resource) => (
          <Tab eventKey={resource.path} title={resource.title} key={resource.path}>
            <ResourcePanel resource={resource} />
          </Tab>
        ))}
        {auth.can("finance.reports") && (
          <Tab eventKey="reports" title="Reports">
            <FinanceReportsPanel />
          </Tab>
        )}
        {canAudit && (
          <Tab eventKey="integrity" title="Billing-GL Integrity">
            <FinanceIntegrityPanel />
          </Tab>
        )}
      </Tabs>
      {visible.length === 0 && !auth.can("finance.reports") && !canApprove && !canAudit && (
        <p>No finance modules are enabled for this account.</p>
      )}
    </>
  );
}
