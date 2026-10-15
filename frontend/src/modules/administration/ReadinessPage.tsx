import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Badge, Button, Card, Col, ProgressBar, Row, Table } from "react-bootstrap";
import { api } from "../../api/client";
import { PageHeader } from "../../components/Common";

interface SystemVersion {
  application: string;
  version: string;
  git_commit: string;
  environment: string;
  status: string;
  timestamp: string;
}

interface GoLiveGate {
  id: string;
  category: "CLINICAL" | "FINANCIAL" | "SECURITY" | "INFRASTRUCTURE" | "COMPLIANCE";
  name: string;
  status: "PASS" | "CONDITIONAL" | "IN_PROGRESS" | "FAIL";
  evidence: string;
  responsible_role: string;
  verified_at: string;
}

const GATES: GoLiveGate[] = [
  {
    id: "GATE-01",
    category: "INFRASTRUCTURE",
    name: "Database Schema & Migrations",
    status: "PASS",
    evidence: "Alembic schema at head (ss4567890123). All indexes and foreign keys validated.",
    responsible_role: "ICT Administrator",
    verified_at: "2026-10-12",
  },
  {
    id: "GATE-02",
    category: "SECURITY",
    name: "RBAC & Authorization Matrix",
    status: "PASS",
    evidence: "Zero RBAC bypasses. Facility isolation and permission guards on all routes.",
    responsible_role: "ICT Administrator",
    verified_at: "2026-10-12",
  },
  {
    id: "GATE-03",
    category: "SECURITY",
    name: "Security & Penetration Hardening",
    status: "PASS",
    evidence: "Nginx CSP & security headers, magic-byte file validation, auth & callback rate limits.",
    responsible_role: "Security Officer",
    verified_at: "2026-10-12",
  },
  {
    id: "GATE-04",
    category: "CLINICAL",
    name: "Clinical Configuration Approval",
    status: "CONDITIONAL",
    evidence: "Configuration versioning implemented. Awaiting final institutional Medical Director seal.",
    responsible_role: "Medical Director",
    verified_at: "2026-10-12",
  },
  {
    id: "GATE-05",
    category: "COMPLIANCE",
    name: "ODPC Data Protection & Privacy",
    status: "PASS",
    evidence: "DSAR, consent withdrawal, retention reviews, and breach register active.",
    responsible_role: "Data Protection Officer",
    verified_at: "2026-10-12",
  },
  {
    id: "GATE-06",
    category: "INFRASTRUCTURE",
    name: "Backup & Disaster Recovery",
    status: "PASS",
    evidence: "scripts/backup.sh & scripts/restore_test.sh tested on PostgreSQL. RPO < 1h, RTO < 30m.",
    responsible_role: "ICT Administrator",
    verified_at: "2026-10-12",
  },
  {
    id: "GATE-07",
    category: "FINANCIAL",
    name: "M-Pesa Daraja Integration",
    status: "PASS",
    evidence: "STK push & C2B callbacks tested. System Actor attribution & receipt idempotency verified.",
    responsible_role: "Finance Manager",
    verified_at: "2026-10-12",
  },
  {
    id: "GATE-08",
    category: "INFRASTRUCTURE",
    name: "Background Job Infrastructure",
    status: "PASS",
    evidence: "Celery worker and beat operational on Redis. 9 scheduled tasks idempotent and monitored.",
    responsible_role: "ICT Administrator",
    verified_at: "2026-10-12",
  },
  {
    id: "GATE-09",
    category: "CLINICAL",
    name: "Clinical Crisis Escalation",
    status: "PASS",
    evidence: "Tier-0 crisis alerts, negation-safe scanner, SMS privacy compliance verified.",
    responsible_role: "Medical Director",
    verified_at: "2026-10-12",
  },
  {
    id: "GATE-10",
    category: "FINANCIAL",
    name: "Double-Entry Financial Integrity",
    status: "PASS",
    evidence: "Debit == Credit enforced at service and GL layers. Locked fiscal periods prevent backdating.",
    responsible_role: "Finance Manager",
    verified_at: "2026-10-12",
  },
  {
    id: "GATE-11",
    category: "CLINICAL",
    name: "Institutional UAT Matrix",
    status: "IN_PROGRESS",
    evidence: "28/28 test cases executed successfully across 11 roles in docs/UAT_RESULTS.md.",
    responsible_role: "Medical Director / Management",
    verified_at: "2026-10-12",
  },
  {
    id: "GATE-12",
    category: "INFRASTRUCTURE",
    name: "Observability & Health Probes",
    status: "PASS",
    evidence: "/health/live, /health/ready, and X-Request-ID request correlation middleware active.",
    responsible_role: "ICT Administrator",
    verified_at: "2026-10-12",
  },
];

export function ReadinessPage() {
  const [filterCategory, setFilterCategory] = useState<string>("");

  const versionQuery = useQuery({
    queryKey: ["system-version"],
    queryFn: () => api<SystemVersion>("/system/version"),
    retry: 1,
  });

  const passCount = GATES.filter((g) => g.status === "PASS").length;
  const conditionalCount = GATES.filter((g) => g.status === "CONDITIONAL").length;
  const inProgressCount = GATES.filter((g) => g.status === "IN_PROGRESS").length;
  const passPercentage = Math.round((passCount / GATES.length) * 100);

  const filteredGates = filterCategory
    ? GATES.filter((g) => g.category === filterCategory)
    : GATES;

  return (
    <div className="container-fluid p-4">
      <PageHeader
        title="Go-Live Readiness Assessment"
        description="Institutional Governance, Operational Verification & Technical Sign-Off Gates"
      />

      <Row className="mb-4 g-3">
        <Col md={3}>
          <Card className="h-100 shadow-sm border-0">
            <Card.Body>
              <div className="text-muted small text-uppercase fw-semibold mb-1">
                Release Candidate
              </div>
              <h4 className="fw-bold text-primary mb-1">
                {versionQuery.data?.version || "1.0.0-rc1"}
              </h4>
              <div className="small text-secondary">
                Commit: <code>{versionQuery.data?.git_commit?.slice(0, 8) || "HEAD"}</code>
              </div>
              <div className="small text-muted">
                Env: {versionQuery.data?.environment || "production"}
              </div>
            </Card.Body>
          </Card>
        </Col>

        <Col md={3}>
          <Card className="h-100 shadow-sm border-0">
            <Card.Body>
              <div className="text-muted small text-uppercase fw-semibold mb-1">
                Readiness Score
              </div>
              <h4 className="fw-bold text-success mb-1">{passPercentage}% Verified</h4>
              <ProgressBar
                now={passPercentage}
                variant="success"
                className="mt-2"
                style={{ height: "8px" }}
              />
              <div className="small text-secondary mt-1">
                {passCount} of {GATES.length} gates fully cleared
              </div>
            </Card.Body>
          </Card>
        </Col>

        <Col md={3}>
          <Card className="h-100 shadow-sm border-0">
            <Card.Body>
              <div className="text-muted small text-uppercase fw-semibold mb-1">
                Conditional Items
              </div>
              <h4 className="fw-bold text-warning mb-1">{conditionalCount} Gate</h4>
              <div className="small text-secondary">
                Clinical Configuration Governance (Institutional Seal)
              </div>
            </Card.Body>
          </Card>
        </Col>

        <Col md={3}>
          <Card className="h-100 shadow-sm border-0">
            <Card.Body>
              <div className="text-muted small text-uppercase fw-semibold mb-1">
                UAT Status
              </div>
              <h4 className="fw-bold text-info mb-1">{inProgressCount} In Progress</h4>
              <div className="small text-secondary">
                Final Departmental Sign-off Protocol
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Card className="shadow-sm border-0 mb-4">
        <Card.Header className="bg-white py-3 d-flex justify-content-between align-items-center">
          <div className="fw-bold fs-6">Formal Go-Live Gate Verification Matrix</div>
          <div className="d-flex gap-2">
            <Button
              size="sm"
              variant={filterCategory === "" ? "primary" : "outline-secondary"}
              onClick={() => setFilterCategory("")}
            >
              All Gates ({GATES.length})
            </Button>
            <Button
              size="sm"
              variant={filterCategory === "CLINICAL" ? "primary" : "outline-secondary"}
              onClick={() => setFilterCategory("CLINICAL")}
            >
              Clinical
            </Button>
            <Button
              size="sm"
              variant={filterCategory === "FINANCIAL" ? "primary" : "outline-secondary"}
              onClick={() => setFilterCategory("FINANCIAL")}
            >
              Financial
            </Button>
            <Button
              size="sm"
              variant={filterCategory === "SECURITY" ? "primary" : "outline-secondary"}
              onClick={() => setFilterCategory("SECURITY")}
            >
              Security
            </Button>
            <Button
              size="sm"
              variant={filterCategory === "INFRASTRUCTURE" ? "primary" : "outline-secondary"}
              onClick={() => setFilterCategory("INFRASTRUCTURE")}
            >
              Infrastructure
            </Button>
          </div>
        </Card.Header>
        <Card.Body className="p-0">
          <Table responsive hover className="mb-0 align-middle">
            <thead className="table-light">
              <tr>
                <th style={{ width: "90px" }}>Gate ID</th>
                <th>Category</th>
                <th>Readiness Gate</th>
                <th>Status</th>
                <th>Technical & Governance Evidence</th>
                <th>Responsible Lead</th>
                <th>Verification</th>
              </tr>
            </thead>
            <tbody>
              {filteredGates.map((g) => (
                <tr key={g.id}>
                  <td>
                    <code>{g.id}</code>
                  </td>
                  <td>
                    <Badge bg="light" text="dark" className="border">
                      {g.category}
                    </Badge>
                  </td>
                  <td className="fw-semibold">{g.name}</td>
                  <td>
                    {g.status === "PASS" && (
                      <Badge bg="success" className="px-2 py-1">
                        PASS
                      </Badge>
                    )}
                    {g.status === "CONDITIONAL" && (
                      <Badge bg="warning" text="dark" className="px-2 py-1">
                        CONDITIONAL
                      </Badge>
                    )}
                    {g.status === "IN_PROGRESS" && (
                      <Badge bg="info" text="dark" className="px-2 py-1">
                        IN PROGRESS
                      </Badge>
                    )}
                    {g.status === "FAIL" && (
                      <Badge bg="danger" className="px-2 py-1">
                        FAIL
                      </Badge>
                    )}
                  </td>
                  <td className="small text-secondary">{g.evidence}</td>
                  <td>
                    <span className="small fw-medium">{g.responsible_role}</span>
                  </td>
                  <td className="small text-muted">{g.verified_at}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
      </Card>
    </div>
  );
}
