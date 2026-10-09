import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { ErrorNotice } from "../../components/Common";
import type { Page } from "../../types/identity";
import { useAuth } from "../../auth/AuthProvider";

export function CrisisAlerts() {
  const queryClient = useQueryClient();
  const auth = useAuth();
  
  const query = useQuery({
    queryKey: ["dashboard-crisis-alerts"],
    queryFn: () => api<Page<any>>("/clinical/crisis-alerts?page_size=5"),
    enabled: auth.can("clinical.view"),
  });

  const acknowledge = useMutation({
    mutationFn: (id: string) => api(`/clinical/crisis-alerts/${id}/acknowledge`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard-crisis-alerts"] });
    },
  });

  if (!auth.can("clinical.view")) {
      return null;
  }

  return (
    <section className="card mb-4 border-danger border-opacity-50">
      <div className="card-header bg-danger bg-opacity-10 text-danger border-danger border-opacity-25 d-flex justify-content-between align-items-center">
        <h2 className="mb-0 fs-5"><i className="bi bi-exclamation-octagon-fill me-2"></i>Active Crisis Alerts</h2>
      </div>
      <div className="card-body">
        <ErrorNotice error={query.error} />
        {query.data?.items.length ? (
          <ul className="list-group list-group-flush mb-0">
            {query.data.items.map((row) => (
              <li key={row.id} className="list-group-item px-0 py-3">
                <div className="d-flex justify-content-between align-items-start">
                  <div>
                    <div className="fw-bold text-danger mb-1">
                      <i className="bi bi-shield-exclamation me-1"></i> {row.severity} RISK
                    </div>
                    <p className="mb-1 text-dark">Detected keywords: <strong>{row.detected_keywords}</strong></p>
                    <p className="mb-2 text-muted small fst-italic">"{row.text_snippet}..."</p>
                    <div className="small text-secondary">
                        Source: {row.source_entity}
                        {row.client_id && (
                          <span className="ms-2">
                             &middot; <Link to={`/clients/${row.client_id}`}>View Client</Link>
                          </span>
                        )}
                    </div>
                  </div>
                  {auth.can("clinical.create_note") && (
                    <button 
                      className="btn btn-sm btn-outline-danger" 
                      onClick={() => acknowledge.mutate(row.id)}
                      disabled={acknowledge.isPending}
                    >
                      Acknowledge
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mb-0 text-success fw-bold d-flex align-items-center">
            <i className="bi bi-check-circle-fill me-2"></i> No active crisis alerts.
          </p>
        )}
      </div>
    </section>
  );
}
