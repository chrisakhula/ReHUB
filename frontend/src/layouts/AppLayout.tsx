import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { NavLink, Outlet, Link } from "react-router-dom";
import { Button, Offcanvas } from "react-bootstrap";
import { useAuth } from "../auth/AuthProvider";
import { identityApi } from "../api/identity";
import { ErrorNotice } from "../components/Common";
import { CrisisHelpButton } from "../components/CrisisHelpModal";


const navGroups = [
  {
    label: "Workspace",
    links: [
      { to: "/", name: "Dashboard", icon: "grid-1x2", permission: "" },
    ]
  },
  {
    label: "Care",
    links: [
      { to: "/clients", name: "Clients", icon: "people", permission: "client.view" },
      { to: "/referrals", name: "Referrals & screening", icon: "clipboard-check", permission: "referral.view" },
      { to: "/admissions", name: "Admissions", icon: "person-plus", permission: "admission.view" },
      { to: "/assessments", name: "Assessments & risk", icon: "clipboard-pulse", permission: ["assessment.view", "risk.view"] },
      { to: "/rehabilitation", name: "Rehabilitation", icon: "journal-medical", permission: ["therapy.view", "treatment_plan.view", "case_management.view", "programme.view", "family.view"] },
      { to: "/clinical", name: "Clinical care", icon: "heart-pulse", permission: "clinical.view" },
      { to: "/nursing", name: "Nursing station", icon: "activity", permission: "nursing.view" },
      { to: "/laboratory", name: "Investigations", icon: "eyedropper", permission: "lab.view" },
      { to: "/toxicology", name: "Toxicology", icon: "clipboard-data", permission: "lab.view" },
      { to: "/medication", name: "Medication & eMAR", icon: "capsule", permission: "medication.view" },
    ]
  },
    {
    label: "Operations",
    links: [
      { to: "/pharmacy", name: "Pharmacy", icon: "box-seam", permission: "pharmacy.view" },
      { to: "/residential", name: "Residential beds", icon: "building", permission: "residential.view" },
      { to: "/billing/invoices", name: "Billing & Finance", icon: "receipt", permission: "billing.view" },
      { to: "/discharge/plans", name: "Discharge & Aftercare", icon: "box-arrow-right", permission: "discharge.view" },
      { to: "/inventory/items", name: "Inventory", icon: "boxes", permission: "inventory.view" },
      { to: "/staff/profiles", name: "Staff & HR", icon: "person-badge", permission: "staff.view" },
      { to: "/compliance/licences", name: "Compliance & Quality", icon: "shield-check", permission: "compliance.view" },
      { to: "/reporting", name: "Reporting & Analytics", icon: "bar-chart-line", permission: "reporting.view" },
    ]
  },
  {
    label: "Administration",
    links: [
      { to: "/administration/users", name: "Users", icon: "people", permission: "users.manage" },
      { to: "/administration/roles", name: "Roles & permissions", icon: "shield-check", permission: "roles.manage" },
      { to: "/administration/departments", name: "Departments", icon: "diagram-3", permission: "departments.manage" },
      { to: "/administration/audit", name: "Audit trail", icon: "journal-text", permission: "audit.view" },
      { to: "/administration/settings", name: "Institution settings", icon: "gear", permission: "settings.manage" },
    ]
  }
];
export function AppLayout() {
  const auth = useAuth();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("theme") || "light";
  });
  
  useEffect(() => {
    document.documentElement.setAttribute("data-bs-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);
  
  const toggleTheme = () => {
    setTheme(prev => prev === "light" ? "dark" : "light");
  };

  const settings = useQuery({
    queryKey: ["settings"],
    queryFn: identityApi.settings,
  });
  useEffect(() => {
    document.title =
      settings.data?.system_name ?? "ARS Rehabilitation Management System";
  }, [settings.data?.system_name]);
  const navigation = (
    <>
      <div className="sidebar-brand">
        <div className="brand-mark small-mark">
          {settings.data?.logo_url ? (
            <img src={settings.data.logo_url} alt="Institution logo" />
          ) : (
            "ARS"
          )}
        </div>
        <div>
          <strong>{settings.data?.short_name ?? "ARS RMS"}</strong>
          <small>Rehabilitation management</small>
        </div>
      </div>
      <nav aria-label="Main navigation">
        {navGroups.map((group) => {
          const visibleLinks = group.links.filter(
            (l) =>
              !l.permission ||
              (Array.isArray(l.permission)
                ? l.permission.some((p) => auth.can(p))
                : auth.can(l.permission)),
          );
          if (visibleLinks.length === 0) return null;
          
          return (
            <div key={group.label} className="nav-group mb-3">
              <div className="nav-section-label">{group.label}</div>
              {visibleLinks.map((l) => (
                <NavLink
                  key={l.to}
                  to={l.to}
                  end={l.to === "/"}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    `sidebar-link ${isActive ? "active" : ""}`
                  }
                >
                  <i className={`bi bi-${l.icon}`} aria-hidden="true" />
                  {l.name}
                </NavLink>
              ))}
            </div>
          );
        })}
      </nav>
      
      <div className="sidebar-foot">
        <i className="bi bi-lock" aria-hidden="true" /> Restricted institutional
        access
        <br />
        <span>Care modules, Phases 1-5</span>
      </div>
    </>
  );
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <aside className="desktop-sidebar">{navigation}</aside>
      <Offcanvas show={open} onHide={() => setOpen(false)}>
        <Offcanvas.Header closeButton>
          <Offcanvas.Title>Navigation</Offcanvas.Title>
        </Offcanvas.Header>
        <Offcanvas.Body className="mobile-sidebar">{navigation}</Offcanvas.Body>
      </Offcanvas>
      <div className="app-body">
        <header className="topbar">
          <div className="d-flex align-items-center gap-3">
            <Button
              variant="outline-secondary"
              className="d-lg-none"
              aria-label="Open navigation"
              onClick={() => setOpen(true)}
            >
              <i className="bi bi-list" />
            </Button>
            <span className="institution-name">
              {settings.data?.name ?? "ARS Rehabilitation Institution"}
            </span>
            <div className="ms-3 d-flex align-items-center gap-2">
              <Button variant="outline-secondary" size="sm" onClick={toggleTheme} aria-label="Toggle theme">
                <i className={`bi bi-${theme === 'dark' ? 'sun' : 'moon'}`} />
              </Button>
              <CrisisHelpButton />
            </div>
          </div>
          <div className="topbar-user">
            <div>
              <strong>{auth.user?.full_name}</strong>
              <small>
                {auth.user?.roles.map((r) => r.name).join(", ") ||
                  "Staff member"}
              </small>
            </div>
            <Button
              variant="outline-secondary"
              size="sm"
              onClick={async () => {
                try {
                  await auth.logout();
                } catch (e) {
                  setError(String(e));
                }
              }}
            >
              Sign out
            </Button>
          </div>
        </header>
        <main id="main-content" className="main-content">
          <ErrorNotice error={error} />
          <Outlet />
        </main>
        <footer className="app-footer">
          <span>
            {settings.data?.short_name ?? "ARS RMS"} · Authorised staff only
          </span>
          <Link to="/change-password">Change password</Link>
        </footer>
      </div>
    </div>
  );
}
