import { useEffect, useState } from "react";
import { Row, Col, Card } from "react-bootstrap";
import { api } from "../../api/client";

interface DashboardMetrics {
  active_clients: number;
  current_occupancy: number;
  pending_discharges: number;
  recent_incidents: number;
  outstanding_invoices: number;
}

export function ReportingPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const data = await api<DashboardMetrics>("/reporting/dashboard");
        setMetrics(data);
      } catch (err) {
        console.error("Failed to load metrics", err);
      } finally {
        setLoading(false);
      }
    };
    fetchMetrics();
  }, []);

  if (loading) return <div className="p-4">Loading dashboards...</div>;

  return (
    <div className="reporting-workspace p-4">
      <div className="mb-4">
        <h1 className="h3">Management Dashboard</h1>
        <p className="text-secondary">Live operational metrics and facility overview.</p>
      </div>

      <Row className="g-4 mb-4">
        <Col md={3}>
          <Card className="h-100 border-0 shadow-sm">
            <Card.Body>
              <h6 className="text-muted mb-2">Active Clients</h6>
              <h2 className="mb-0">{metrics?.active_clients || 0}</h2>
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card className="h-100 border-0 shadow-sm">
            <Card.Body>
              <h6 className="text-muted mb-2">Current Occupancy</h6>
              <h2 className="mb-0">{metrics?.current_occupancy || 0}%</h2>
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card className="h-100 border-0 shadow-sm">
            <Card.Body>
              <h6 className="text-muted mb-2">Pending Discharges</h6>
              <h2 className="mb-0">{metrics?.pending_discharges || 0}</h2>
            </Card.Body>
          </Card>
        </Col>
        <Col md={3}>
          <Card className="h-100 border-0 shadow-sm">
            <Card.Body>
              <h6 className="text-muted mb-2">Outstanding Invoices</h6>
              <h2 className="mb-0">{metrics?.outstanding_invoices || 0}</h2>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row className="g-4">
        <Col md={6}>
          <Card className="h-100 border-0 shadow-sm">
            <Card.Header className="bg-white border-0 pt-4 pb-0">
              <h6 className="mb-0">Clinical Reports</h6>
            </Card.Header>
            <Card.Body>
              <ul className="list-unstyled">
                <li className="mb-2"><a href="#">Active Diagnoses</a></li>
                <li className="mb-2"><a href="#">Medication Adherence</a></li>
                <li className="mb-2"><a href="#">Treatment Outcomes</a></li>
              </ul>
            </Card.Body>
          </Card>
        </Col>
        <Col md={6}>
          <Card className="h-100 border-0 shadow-sm">
            <Card.Header className="bg-white border-0 pt-4 pb-0">
              <h6 className="mb-0">Rehabilitation Reports</h6>
            </Card.Header>
            <Card.Body>
              <ul className="list-unstyled">
                <li className="mb-2"><a href="#">Programme Attendance</a></li>
                <li className="mb-2"><a href="#">Relapse Rates</a></li>
                <li className="mb-2"><a href="#">Discharge Readiness</a></li>
              </ul>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
