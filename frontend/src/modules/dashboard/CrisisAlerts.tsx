import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Modal, Button, Form, Badge } from "react-bootstrap";
import { api } from "../../api/client";
import { ErrorNotice } from "../../components/Common";
import type { Page } from "../../types/identity";
import { useAuth } from "../../auth/AuthProvider";

interface CrisisAlertItem {
  id: string;
  alert_reference?: string;
  client_id?: string;
  admission_id?: string;
  trigger: string;
  severity: string;
  status: string;
  detected_keywords: string;
  text_snippet: string;
  escalation_level: number;
  escalation_history?: Array<{
    timestamp: string;
    action: string;
    reason?: string;
    user_id?: string;
  }>;
  created_at?: string;
}

export function CrisisAlerts() {
  const queryClient = useQueryClient();
  const auth = useAuth();

  const [activeModal, setActiveModal] = useState<"review" | "resolve" | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<CrisisAlertItem | null>(null);
  const [responseNotes, setResponseNotes] = useState("");
  const [interventionPlan, setInterventionPlan] = useState("");
  const [resolutionNotes, setResolutionNotes] = useState("");

  const query = useQuery({
    queryKey: ["dashboard-crisis-alerts"],
    queryFn: () => api<Page<CrisisAlertItem>>("/clinical/crisis-alerts?limit=10"),
    enabled: auth.can("clinical.view"),
    refetchInterval: 15000, // Poll every 15s for urgent patient safety
  });

  const acknowledge = useMutation({
    mutationFn: (id: string) => api(`/clinical/crisis-alerts/${id}/acknowledge`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard-crisis-alerts"] });
    },
  });

  const reviewMutation = useMutation({
    mutationFn: ({ id, response, intervention }: { id: string; response: string; intervention: string }) =>
      api(`/clinical/crisis-alerts/${id}/review`, {
        method: "POST",
        body: JSON.stringify({ response, intervention }),
      }),
    onSuccess: () => {
      setActiveModal(null);
      setSelectedAlert(null);
      setResponseNotes("");
      setInterventionPlan("");
      queryClient.invalidateQueries({ queryKey: ["dashboard-crisis-alerts"] });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id, resolution }: { id: string; resolution: string }) =>
      api(`/clinical/crisis-alerts/${id}/resolve`, {
        method: "POST",
        body: JSON.stringify({ resolution }),
      }),
    onSuccess: () => {
      setActiveModal(null);
      setSelectedAlert(null);
      setResolutionNotes("");
      queryClient.invalidateQueries({ queryKey: ["dashboard-crisis-alerts"] });
    },
  });

  if (!auth.can("clinical.view")) {
    return null;
  }

  const items = query.data?.items || [];

  return (
    <>
      <section className="card mb-4 border-danger border-opacity-50 shadow-sm">
        <div className="card-header bg-danger bg-opacity-10 text-danger border-danger border-opacity-25 d-flex justify-content-between align-items-center py-2">
          <h2 className="mb-0 fs-6 fw-bold">
            <i className="bi bi-shield-exclamation me-2"></i>Active Crisis Escalation Roster
          </h2>
          <span className="badge bg-danger rounded-pill px-2 py-1">
            {items.length} Active Alert{items.length !== 1 ? "s" : ""}
          </span>
        </div>
        <div className="card-body p-3">
          <ErrorNotice error={query.error} />
          {items.length > 0 ? (
            <div className="list-group list-group-flush">
              {items.map((row) => (
                <div key={row.id} className="list-group-item px-0 py-2 border-bottom">
                  <div className="d-flex justify-content-between align-items-start">
                    <div>
                      <div className="d-flex align-items-center gap-2 mb-1">
                        <span className="badge bg-danger">{row.severity}</span>
                        <span className={`badge ${row.status === "ESCALATED" ? "bg-warning text-dark" : "bg-secondary"}`}>
                          {row.status}
                        </span>
                        {row.alert_reference && (
                          <span className="text-muted small font-monospace">{row.alert_reference}</span>
                        )}
                        {row.escalation_level > 0 && (
                          <Badge bg="danger" className="text-uppercase">
                            Escalation Tier {row.escalation_level}
                          </Badge>
                        )}
                      </div>
                      <p className="mb-1 text-dark small">
                        <strong>Trigger:</strong> {row.trigger} &bull; Keywords: <em>{row.detected_keywords}</em>
                      </p>
                      <p className="mb-1 text-muted small fst-italic">"{row.text_snippet.slice(0, 160)}..."</p>
                      <div className="small text-secondary">
                        {row.client_id && (
                          <Link to={`/clients/${row.client_id}`} className="text-decoration-none">
                            <i className="bi bi-person-badge me-1"></i>Client Profile
                          </Link>
                        )}
                        {row.created_at && (
                          <span className="ms-2 text-muted">
                            &middot; Logged {new Date(row.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="d-flex flex-column gap-1 align-items-end">
                      {auth.can("clinical.create_note") && (
                        <>
                          {(row.status === "NEW" || row.status === "ESCALATED" || row.status === "DETECTED") && (
                            <button
                              className="btn btn-sm btn-outline-danger"
                              onClick={() => acknowledge.mutate(row.id)}
                              disabled={acknowledge.isPending}
                            >
                              <i className="bi bi-check2-circle me-1"></i>Acknowledge
                            </button>
                          )}

                          {row.status === "ACKNOWLEDGED" && (
                            <button
                              className="btn btn-sm btn-outline-primary"
                              onClick={() => {
                                setSelectedAlert(row);
                                setActiveModal("review");
                              }}
                            >
                              <i className="bi bi-pencil-square me-1"></i>Review / Plan
                            </button>
                          )}

                          {row.status === "UNDER_REVIEW" && (
                            <button
                              className="btn btn-sm btn-outline-success"
                              onClick={() => {
                                setSelectedAlert(row);
                                setActiveModal("resolve");
                              }}
                            >
                              <i className="bi bi-check-all me-1"></i>Resolve Crisis
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="mb-0 text-success small fw-medium d-flex align-items-center">
              <i className="bi bi-check-circle-fill me-2"></i> All clear. No active critical risk escalations.
            </p>
          )}
        </div>
      </section>

      {/* Review Modal */}
      <Modal show={activeModal === "review"} onHide={() => setActiveModal(null)} centered>
        <Modal.Header closeButton>
          <Modal.Title className="fs-6">
            Clinical Intervention for {selectedAlert?.alert_reference || "Crisis Alert"}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label className="small fw-bold">Clinical Response Summary</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                placeholder="Document immediate clinical findings and client current state..."
                value={responseNotes}
                onChange={(e) => setResponseNotes(e.target.value)}
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label className="small fw-bold">Safety Intervention Plan</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                placeholder="e.g. Assigned 1:1 continuous nursing observation, removed sharp objects, scheduled urgent psychiatric consultation..."
                value={interventionPlan}
                onChange={(e) => setInterventionPlan(e.target.value)}
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" size="sm" onClick={() => setActiveModal(null)}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            disabled={!responseNotes || !interventionPlan || reviewMutation.isPending}
            onClick={() => {
              if (selectedAlert) {
                reviewMutation.mutate({
                  id: selectedAlert.id,
                  response: responseNotes,
                  intervention: interventionPlan,
                });
              }
            }}
          >
            Save Intervention Plan
          </Button>
        </Modal.Footer>
      </Modal>

      {/* Resolve Modal */}
      <Modal show={activeModal === "resolve"} onHide={() => setActiveModal(null)} centered>
        <Modal.Header closeButton>
          <Modal.Title className="fs-6">
            Resolve Crisis {selectedAlert?.alert_reference || "Alert"}
          </Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form>
            <Form.Group className="mb-3">
              <Form.Label className="small fw-bold">Resolution & Disposition Notes</Form.Label>
              <Form.Control
                as="textarea"
                rows={4}
                placeholder="Document resolution outcome, client stabilization, and ongoing monitoring schedule..."
                value={resolutionNotes}
                onChange={(e) => setResolutionNotes(e.target.value)}
              />
            </Form.Group>
          </Form>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" size="sm" onClick={() => setActiveModal(null)}>
            Cancel
          </Button>
          <Button
            variant="success"
            size="sm"
            disabled={!resolutionNotes || resolveMutation.isPending}
            onClick={() => {
              if (selectedAlert) {
                resolveMutation.mutate({
                  id: selectedAlert.id,
                  resolution: resolutionNotes,
                });
              }
            }}
          >
            Confirm Clinical Resolution
          </Button>
        </Modal.Footer>
      </Modal>
    </>
  );
}
