import { Link } from "react-router-dom";
import { useAuth } from "../../auth/AuthProvider";
import "./DashboardPage.css";

export function DashboardPage() {
  const auth = useAuth();
  
  // Format date to e.g., "Tuesday, 6 October 2026"
  const currentDate = new Intl.DateTimeFormat('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  }).format(new Date());

  const workspaces = [
    {
      permission: "client.view",
      to: "/clients",
      icon: "people",
      title: "Client registry",
      description: "Find and review authorised client records.",
    },
    {
      permission: "admission.view",
      to: "/admissions",
      icon: "clipboard",
      title: "Admissions",
      description: "Manage care episodes and bed assignments.",
    },
    {
      permission: ["therapy.view", "treatment_plan.view"],
      to: "/rehabilitation",
      icon: "journal-medical",
      title: "Rehabilitation",
      description: "Continue treatment plans, sessions, programmes, and family work.",
    },
    {
      permission: "clinical.view",
      to: "/clinical",
      icon: "heart-pulse",
      title: "Clinical care",
      description: "Review encounters, diagnoses, orders, and care plans.",
    },
    {
      permission: "nursing.view",
      to: "/nursing",
      icon: "activity",
      title: "Nursing station",
      description: "Record observations, handovers, and nursing care.",
    },
    {
      permission: "medication.view",
      to: "/medication",
      icon: "capsule",
      title: "Medication & eMAR",
      description: "Review prescriptions, scheduled doses, and administration outcomes.",
    },
    {
      permission: "pharmacy.view",
      to: "/pharmacy",
      icon: "box-seam",
      title: "Pharmacy",
      description: "Manage medication catalogue, stock, batches, and dispensing.",
    },
    {
      permission: "residential.view",
      to: "/residential",
      icon: "building",
      title: "Residential beds",
      description: "Manage beds, room assignments, and occupancy.",
    },
  ].filter(({ permission }) =>
    Array.isArray(permission)
      ? permission.some((code) => auth.can(code))
      : auth.can(permission),
  );

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div className="dashboard-breadcrumb">
          Workspace / <span>Overview</span>
          <span className="badge-design-sample">Synthetic design sample</span>
        </div>
        
        <div className="dashboard-title-row">
          <h1>Workspace overview</h1>
          <span className="dashboard-date">{currentDate}</span>
        </div>
        <p className="dashboard-subtitle">Your authorised workspaces, together in one place.</p>
      </div>

      <div className="dashboard-alert">
        <div className="alert-content">
          <i className="bi bi-shield"></i>
          <span>Access follows your approved roles and care assignments.</span>
        </div>
        <Link to="/administration/roles" className="alert-link">
          View my access <i className="bi bi-arrow-right"></i>
        </Link>
      </div>

      <div className="dashboard-grid">
        {/* Left Column */}
        <div className="dashboard-main-col">
          <div className="dash-card">
            <div className="dash-card-header border-0 pb-0">
              <h2>Open a workspace</h2>
              <span className="text-secondary small">Care & operations</span>
            </div>
            <div className="workspace-grid mt-3">
              {workspaces.map(({ to, icon, title, description }) => (
                <Link className="workspace-card-item" key={to} to={to}>
                  <div className="workspace-icon">
                    <i className={`bi bi-${icon}`} />
                  </div>
                  <div className="workspace-text">
                    <strong>{title}</strong>
                    <small>{description}</small>
                  </div>
                  <div className="workspace-arrow">
                    <i className="bi bi-arrow-right" />
                  </div>
                </Link>
              ))}
              {workspaces.length === 0 && (
                <div className="p-4 text-center text-muted w-100" style={{ gridColumn: "1 / -1" }}>
                  No care workspaces are enabled for this account.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="dashboard-side-col">
          <div className="dash-card mb-4 risk-register-card">
            <div className="dash-card-header d-flex justify-content-between align-items-center">
              <h2><i className="bi bi-file-earmark-text me-2 text-primary"></i> Risk register</h2>
              <Link to="/assessments" className="dash-link">Open risk register <i className="bi bi-arrow-right"></i></Link>
            </div>
            <div className="risk-empty-state">
              <div className="shield-circle">
                <i className="bi bi-shield"></i>
              </div>
              <h3 className="mt-3">No records in your permitted scope</h3>
              <p className="text-secondary small mt-1">This view only includes records you are<br/>authorised to see.</p>
            </div>
          </div>

          <div className="dash-card">
            <div className="dash-card-header">
              <h2><i className="bi bi-gear me-2 text-primary"></i> Your workspace access</h2>
            </div>
            <div className="dash-card-body pt-3">
              <div className="user-profile-row mb-4">
                <div className="user-avatar">
                  {auth.user?.full_name?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || 'DS'}
                </div>
                <div className="user-info">
                  <strong>{auth.user?.full_name || 'Demo staff'}</strong>
                  <small>Assigned care-team access</small>
                </div>
              </div>
              
              <table className="access-table mb-3">
                <tbody>
                  <tr>
                    <td className="text-secondary">Care assignment:</td>
                    <td className="text-end">Required</td>
                  </tr>
                  <tr>
                    <td className="text-secondary">Clinical notes:</td>
                    <td className="text-end">Scoped access</td>
                  </tr>
                </tbody>
              </table>
              
              <Link to="/administration/users" className="dash-link border-top pt-3 d-block">
                View access details <i className="bi bi-arrow-right"></i>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="dash-card mt-4">
        <div className="dash-card-body py-3 d-flex flex-column flex-md-row align-items-md-center gap-4">
          <div className="continue-header me-auto pe-4 border-end-md">
            <h2 className="d-flex align-items-center mb-1">
              <i className="bi bi-clock me-2 text-primary fs-5"></i> Continue your work
            </h2>
            <span className="text-secondary small">Choose a workspace to continue.</span>
          </div>
          
          <div className="quick-actions d-flex flex-wrap gap-3 flex-grow-1">
            <Link to="/clients" className="quick-action-link flex-grow-1">
              <div className="d-flex align-items-center">
                <i className="bi bi-people me-3 text-primary fs-5"></i>
                <div>
                  <strong>Find a client</strong>
                  <small className="d-block text-secondary">Search and open an authorised client record.</small>
                </div>
              </div>
              <i className="bi bi-arrow-right arrow ms-auto text-primary"></i>
            </Link>
            
            <Link to="/nursing" className="quick-action-link flex-grow-1 border-start px-3">
              <div className="d-flex align-items-center">
                <i className="bi bi-activity me-3 text-primary fs-5"></i>
                <div>
                  <strong>Open nursing station</strong>
                  <small className="d-block text-secondary">Record observations and handovers.</small>
                </div>
              </div>
              <i className="bi bi-arrow-right arrow ms-auto text-primary"></i>
            </Link>

            <Link to="/clinical" className="quick-action-link flex-grow-1 border-start px-3">
              <div className="d-flex align-items-center">
                <i className="bi bi-journal-text me-3 text-primary fs-5"></i>
                <div>
                  <strong>Review care plans</strong>
                  <small className="d-block text-secondary">View and continue existing care plans.</small>
                </div>
              </div>
              <i className="bi bi-arrow-right arrow ms-auto text-primary"></i>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
