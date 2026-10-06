import type { ReactNode } from "react";
import { Alert, Button } from "react-bootstrap";

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">Rehabilitation Management</div>
        <h1>{title}</h1>
        <p className="text-secondary mb-0">{description}</p>
      </div>
      {action}
    </div>
  );
}
export function ErrorNotice({ error }: { error: unknown }) {
  return error ? (
    <Alert variant="danger" role="alert">
      {error instanceof Error ? error.message : String(error)}
    </Alert>
  ) : null;
}
export function Loading() {
  return (
    <div className="page-skeleton" aria-busy="true">
      <div className="skeleton-header">
        <div className="skeleton-line" style={{ width: "20%", height: "1.5rem" }} />
        <div className="skeleton-line mt-2" style={{ width: "40%" }} />
      </div>
      <div className="skeleton-body mt-4">
        <div className="skeleton-line mb-3" />
        <div className="skeleton-line mb-3" />
        <div className="skeleton-line mb-3" />
        <div className="skeleton-line w-75" />
      </div>
    </div>
  );
}

export function ResponsiveTable({ children }: { children: ReactNode }) {
  return <div className="table-responsive-lg">{children}</div>;
}
export function Pagination({
  page,
  total,
  size = 20,
  onChange,
}: {
  page: number;
  total: number;
  size?: number;
  onChange: (value: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / size));
  return (
    <div className="table-footer">
      <span>
        {total} records · Page {page} of {pages}
      </span>
      <div className="d-flex gap-2">
        <Button
          variant="outline-secondary"
          size="sm"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          Previous
        </Button>
        <Button
          variant="outline-secondary"
          size="sm"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty-state">{children}</div>;
}
