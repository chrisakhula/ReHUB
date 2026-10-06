import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import { ErrorNotice } from "../../components/Common";
import type { Page } from "../../types/identity";
import type { Entity } from "../care/types";

export function RiskAlerts() {
  const query = useQuery({
    queryKey: ["dashboard-risk-alerts"],
    queryFn: () => api<Page<Entity>>("/rehabilitation/risk-alerts?page_size=5"),
  });
  return (
    <section className="card mb-4">
      <div className="card-header">
        <h2>Active high and critical risks</h2>
        <Link to="/assessments">Review risk register</Link>
      </div>
      <div className="card-body">
        <ErrorNotice error={query.error} />
        {query.data?.items.length ? (
          <ul className="mb-0">
            {query.data.items.map((row) => (
              <li key={row.id} className="mb-2">
                <Link to={`/assessments?admission_id=${row.admission_id}`}>
                  {String(row.level)} ·{" "}
                  {String(row.risk_type).replaceAll("_", " ")} · Review{" "}
                  {String(row.review_date)}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mb-0 text-secondary">
            No active high or critical risk records.
          </p>
        )}
      </div>
    </section>
  );
}
