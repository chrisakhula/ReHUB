import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge, Button, Form, Modal, Table } from "react-bootstrap";
import { api } from "../../api/client";
import {
  Empty,
  ErrorNotice,
  Loading,
  PageHeader,
  Pagination,
} from "../../components/Common";

interface BackgroundJobLog {
  id: string;
  task_name: string;
  celery_task_id?: string;
  status: "QUEUED" | "RUNNING" | "SUCCESS" | "FAILED" | "RETRYING" | "CANCELLED";
  facility_id?: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds?: number;
  retries: number;
  failure_message?: string;
  next_scheduled_execution?: string;
  created_at: string;
}

interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

const AVAILABLE_TASKS = [
  { id: "generate_emar_rounds", name: "Generate eMAR Medication Rounds" },
  { id: "detect_overdue_medications", name: "Detect Overdue Medication Doses" },
  { id: "escalate_critical_alerts", name: "Escalate Unacknowledged Crisis Alerts" },
  { id: "detect_overdue_risk_reviews", name: "Detect Overdue Clinical Risk Reviews" },
  { id: "check_compliance_expiry", name: "Scan Statutory Licences & Expiry" },
  { id: "process_aftercare_milestones", name: "Scan Aftercare Recovery Milestones" },
  { id: "check_pharmacy_batches", name: "Scan Expiring Drug Batches & Stock" },
  { id: "check_staff_licence_expiry", name: "Scan Staff Clinical Licences" },
  { id: "check_overdue_invoices", name: "Scan Overdue Invoices & Reconciliation" },
];

export function JobsPage() {
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [taskName, setTaskName] = useState("");
  const [selectedError, setSelectedError] = useState<string | null>(null);
  const [triggerTask, setTriggerTask] = useState("");

  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: ["background-jobs", page, status, taskName],
    queryFn: () =>
      api<Page<BackgroundJobLog>>(
        `/administration/jobs?page=${page}${status ? `&status=${encodeURIComponent(status)}` : ""}${taskName ? `&task_name=${encodeURIComponent(taskName)}` : ""}`,
      ),
    refetchInterval: 10000, // Poll every 10 seconds for real-time monitoring
  });

  const triggerMutation = useMutation({
    mutationFn: (task: string) =>
      api(`/administration/jobs/trigger/${task}`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["background-jobs"] });
      setTriggerTask("");
    },
  });

  const getStatusBadge = (s: string) => {
    switch (s) {
      case "SUCCESS":
        return <Badge bg="success">SUCCESS</Badge>;
      case "RUNNING":
        return <Badge bg="primary">RUNNING</Badge>;
      case "FAILED":
        return <Badge bg="danger">FAILED</Badge>;
      case "RETRYING":
        return <Badge bg="warning" text="dark">RETRYING</Badge>;
      case "QUEUED":
        return <Badge bg="secondary">QUEUED</Badge>;
      default:
        return <Badge bg="dark">{s}</Badge>;
    }
  };

  return (
    <>
      <PageHeader
        title="Background Job Monitoring"
        description="Monitor automated scheduled tasks, Celery workers, and background engine execution health."
      />

      <section className="card mb-4 p-3">
        <div className="d-flex justify-content-between align-items-center flex-wrap gap-3">
          <div className="d-flex gap-3 align-items-center flex-wrap">
            <Form.Group controlId="filter-status" className="mb-0">
              <Form.Label className="small text-muted mb-1">Status Filter</Form.Label>
              <Form.Select
                size="sm"
                value={status}
                onChange={(e) => {
                  setStatus(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All Statuses</option>
                <option value="SUCCESS">SUCCESS</option>
                <option value="RUNNING">RUNNING</option>
                <option value="FAILED">FAILED</option>
                <option value="QUEUED">QUEUED</option>
                <option value="RETRYING">RETRYING</option>
              </Form.Select>
            </Form.Group>

            <Form.Group controlId="filter-task" className="mb-0">
              <Form.Label className="small text-muted mb-1">Task Filter</Form.Label>
              <Form.Select
                size="sm"
                value={taskName}
                onChange={(e) => {
                  setTaskName(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All Tasks</option>
                {AVAILABLE_TASKS.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </Form.Select>
            </Form.Group>
          </div>

          <div className="d-flex gap-2 align-items-end">
            <Form.Group controlId="trigger-select" className="mb-0">
              <Form.Label className="small text-muted mb-1">Trigger Scheduled Task</Form.Label>
              <div className="d-flex gap-2">
                <Form.Select
                  size="sm"
                  value={triggerTask}
                  onChange={(e) => setTriggerTask(e.target.value)}
                >
                  <option value="">Select task to trigger...</option>
                  {AVAILABLE_TASKS.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </Form.Select>
                <Button
                  size="sm"
                  variant="primary"
                  disabled={!triggerTask || triggerMutation.isPending}
                  onClick={() => triggerMutation.mutate(triggerTask)}
                >
                  {triggerMutation.isPending ? "Executing..." : "Run Now"}
                </Button>
              </div>
            </Form.Group>
          </div>
        </div>
      </section>

      <section className="card">
        {query.isLoading ? (
          <Loading />
        ) : query.isError ? (
          <ErrorNotice error={query.error} />
        ) : !query.data?.items.length ? (
          <Empty>No background task executions recorded yet. Scheduled tasks will appear here as they run.</Empty>
        ) : (
          <>
            <Table responsive hover className="align-middle mb-0">
              <thead>
                <tr>
                  <th>Task Name</th>
                  <th>Status</th>
                  <th>Started (EAT)</th>
                  <th>Completed (EAT)</th>
                  <th>Duration</th>
                  <th>Retries</th>
                  <th>Actions / Diagnostics</th>
                </tr>
              </thead>
              <tbody>
                {query.data.items.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <span className="fw-semibold text-primary">{job.task_name}</span>
                      {job.celery_task_id && (
                        <div className="small text-muted font-monospace" style={{ fontSize: "0.75rem" }}>
                          ID: {job.celery_task_id.slice(0, 12)}...
                        </div>
                      )}
                    </td>
                    <td>{getStatusBadge(job.status)}</td>
                    <td className="small text-nowrap">
                      {job.started_at ? new Date(job.started_at).toLocaleString() : "—"}
                    </td>
                    <td className="small text-nowrap">
                      {job.completed_at ? new Date(job.completed_at).toLocaleString() : "—"}
                    </td>
                    <td>
                      {job.duration_seconds !== null && job.duration_seconds !== undefined
                        ? `${job.duration_seconds.toFixed(2)}s`
                        : "—"}
                    </td>
                    <td>{job.retries}</td>
                    <td>
                      {job.failure_message ? (
                        <Button
                          size="sm"
                          variant="outline-danger"
                          onClick={() => setSelectedError(job.failure_message || "")}
                        >
                          View Error
                        </Button>
                      ) : (
                        <span className="text-muted small">OK</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
            <Pagination
              page={page}
              total={query.data.total}
              size={query.data.page_size}
              onChange={setPage}
            />
          </>
        )}
      </section>

      {/* Diagnostics / Error Modal */}
      <Modal show={!!selectedError} onHide={() => setSelectedError(null)} size="lg" centered>
        <Modal.Header closeButton>
          <Modal.Title className="text-danger">Task Error Diagnostics</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <pre
            className="p-3 bg-light border rounded font-monospace small"
            style={{ maxHeight: "400px", overflowY: "auto", whiteSpace: "pre-wrap" }}
          >
            {selectedError}
          </pre>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setSelectedError(null)}>
            Close
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
}
