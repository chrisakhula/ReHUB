import { useEffect, useState } from "react";
import { Row, Col, Card, Form, Button, Table } from "react-bootstrap";
import { api } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";

interface ReportResult {
  report_name: string;
  columns: string[];
  rows: Record<string, any>[];
}

export function ReportingPage() {
  const auth = useAuth();
  const [reportType, setReportType] = useState<"clinical" | "financial">("clinical");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReportResult | null>(null);
  const [error, setError] = useState("");

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!auth.can("reporting.view")) {
        setError("You do not have permission to view reports.");
        return;
    }
    
    setLoading(true);
    setError("");
    setResult(null);
    
    try {
      const res = await api.post<ReportResult>(`/api/v1/reporting/${reportType}`, {
        start_date: startDate || undefined,
        end_date: endDate || undefined
      });
      setResult(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to generate report");
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = () => {
    if (!result || result.rows.length === 0) return;
    
    const headers = result.columns.join(",");
    const csvRows = result.rows.map(row => 
      result.columns.map(col => `"${String(row[col] || '').replace(/"/g, '""')}"`).join(",")
    );
    
    const csvString = [headers, ...csvRows].join("\n");
    const blob = new Blob([csvString], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    
    const a = document.createElement("a");
    a.setAttribute("hidden", "");
    a.setAttribute("href", url);
    a.setAttribute("download", `${result.report_name.replace(/\s+/g, "_")}_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div className="reporting-workspace p-4">
      <div className="mb-4">
        <h1 className="h3">Reporting & Analytics</h1>
        <p className="text-muted">Generate and export operational, clinical, and financial reports.</p>
      </div>

      <Row className="g-4 mb-4">
        <Col md={12}>
          <Card className="border-0 shadow-sm">
            <Card.Header className="bg-white border-0 pt-4 pb-0">
              <h6 className="mb-0">Report Generator</h6>
            </Card.Header>
            <Card.Body>
              <Form onSubmit={handleGenerate} className="d-flex flex-wrap gap-3 align-items-end">
                <Form.Group>
                  <Form.Label>Report Type</Form.Label>
                  <Form.Select 
                    value={reportType} 
                    onChange={(e) => setReportType(e.target.value as any)}
                  >
                    <option value="clinical">Clinical Overview</option>
                    <option value="financial">Financial Overview</option>
                  </Form.Select>
                </Form.Group>
                
                <Form.Group>
                  <Form.Label>Start Date (Optional)</Form.Label>
                  <Form.Control 
                    type="date" 
                    value={startDate} 
                    onChange={(e) => setStartDate(e.target.value)} 
                  />
                </Form.Group>
                
                <Form.Group>
                  <Form.Label>End Date (Optional)</Form.Label>
                  <Form.Control 
                    type="date" 
                    value={endDate} 
                    onChange={(e) => setEndDate(e.target.value)} 
                  />
                </Form.Group>

                <Button variant="primary" type="submit" disabled={loading}>
                  {loading ? "Generating..." : "Generate Report"}
                </Button>
              </Form>
              
              {error && <div className="text-danger mt-3">{error}</div>}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {result && (
        <Row className="g-4">
          <Col md={12}>
            <Card className="border-0 shadow-sm">
              <Card.Header className="bg-white border-bottom pt-4 pb-3 d-flex justify-content-between align-items-center">
                <h6 className="mb-0">{result.report_name}</h6>
                <Button variant="outline-secondary" size="sm" onClick={handleExportCSV}>
                  <i className="bi bi-download me-2"></i> Export CSV
                </Button>
              </Card.Header>
              <Card.Body className="p-0">
                <div className="table-responsive">
                  <Table striped hover className="mb-0">
                    <thead className="bg-light">
                      <tr>
                        {result.columns.map((col, idx) => (
                          <th key={idx}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.rows.length === 0 ? (
                        <tr>
                          <td colSpan={result.columns.length} className="text-center py-4 text-muted">
                            No data available for the selected period.
                          </td>
                        </tr>
                      ) : (
                        result.rows.map((row, rowIdx) => (
                          <tr key={rowIdx}>
                            {result.columns.map((col, colIdx) => (
                              <td key={colIdx}>{row[col]}</td>
                            ))}
                          </tr>
                        ))
                      )}
                    </tbody>
                  </Table>
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      )}
    </div>
  );
}
