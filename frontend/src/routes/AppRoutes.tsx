import { lazy, Suspense } from "react";
import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { Loading } from "../components/Common";
import { AppLayout } from "../layouts/AppLayout";
import { LoginPage } from "../modules/auth/LoginPage";
import {
  ChangePasswordPage,
  ForgotPasswordPage,
  ResetPasswordPage,
} from "../modules/auth/PasswordPages";
import { DashboardPage } from "../modules/dashboard/DashboardPage";
import { UsersPage } from "../modules/administration/UsersPage";
import { UserFormPage } from "../modules/administration/UserFormPage";
import { RolesPage } from "../modules/administration/RolesPage";
import { DepartmentsPage } from "../modules/administration/DepartmentsPage";
import { AuditPage } from "../modules/administration/AuditPage";
import { SettingsPage } from "../modules/administration/SettingsPage";

const ClientsPage = lazy(() =>
  import("../modules/clients/ClientsPage").then((module) => ({
    default: module.ClientsPage,
  })),
);
const ReferralsPage = lazy(() =>
  import("../modules/referrals/ReferralsPage").then((module) => ({
    default: module.ReferralsPage,
  })),
);
const AdmissionsPage = lazy(() =>
  import("../modules/admissions/AdmissionsPage").then((module) => ({
    default: module.AdmissionsPage,
  })),
);

const ResidentialPage = lazy(() =>
  import("../modules/residential/ResidentialPage").then((module) => ({
    default: module.ResidentialPage,
  })),
);
const AssessmentsPage = lazy(() =>
  import("../modules/assessments/AssessmentsPage").then((module) => ({
    default: module.AssessmentsPage,
  })),
);
const RehabilitationPage = lazy(() =>
  import("../modules/rehabilitation/RehabilitationPage").then((module) => ({
    default: module.RehabilitationPage,
  })),
);
const ClinicalPage = lazy(() =>
  import("../modules/clinical/ClinicalPage").then((module) => ({
    default: module.ClinicalPage,
  })),
);
const LaboratoryPage = lazy(() =>
  import("../modules/clinical/LaboratoryPage").then((module) => ({
    default: module.LaboratoryPage,
  })),
);
const ToxicologyPage = lazy(() =>
  import("../modules/clinical/ToxicologyPage").then((module) => ({
    default: module.ToxicologyPage,
  })),
);
const NursingPage = lazy(() =>
  import("../modules/nursing/NursingPage").then((module) => ({
    default: module.NursingPage,
  })),
);
const MedicationPage = lazy(() =>
  import("../modules/medication/MedicationPage").then((module) => ({
    default: module.MedicationPage,
  })),
);
const PharmacyPage = lazy(() =>
  import("../modules/pharmacy/PharmacyPage").then((module) => ({
    default: module.PharmacyPage,
  })),
);


const BillingPage = lazy(() => import("../modules/billing/BillingPage").then((m) => ({ default: m.BillingPage })));
const InventoryPage = lazy(() => import("../modules/inventory/InventoryPage").then((m) => ({ default: m.InventoryPage })));
const DischargePage = lazy(() => import("../modules/discharge/DischargePage").then((m) => ({ default: m.DischargePage })));
const ReportingPage = lazy(() => import("../modules/reporting/ReportingPage").then((m) => ({ default: m.ReportingPage })));
const CompliancePage = lazy(() => import("../modules/compliance/CompliancePage").then((m) => ({ default: m.CompliancePage })));
const StaffPage = lazy(() => import("../modules/staff/StaffPage").then((m) => ({ default: m.StaffPage })));
function AuthGuard() {
  const auth = useAuth();
  if (auth.loading) return <Loading />;
  if (!auth.user) return <Navigate to="/login" replace />;
  return <Outlet />;
}
function PasswordGuard() {
  return useAuth().user?.force_password_change ? (
    <Navigate to="/change-password" replace />
  ) : (
    <Outlet />
  );
}
function PermissionGuard({ permission }: { permission: string | string[] }) {
  const auth = useAuth();
  return (
    Array.isArray(permission)
      ? permission.some((p) => auth.can(p))
      : auth.can(permission)
  ) ? (
    <Outlet />
  ) : (
    <div role="alert">
      <h1>Access restricted</h1>
      <p>Your account does not have permission to access this section.</p>
    </div>
  );
}
export function AppRoutes() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route element={<AuthGuard />}>
          <Route path="/change-password" element={<ChangePasswordPage />} />
          <Route element={<PasswordGuard />}>
            <Route element={<AppLayout />}>
              <Route index element={<DashboardPage />} />
              <Route element={<PermissionGuard permission="client.view" />}>
                <Route path="/clients" element={<ClientsPage />} />
              </Route>
              <Route element={<PermissionGuard permission="referral.view" />}>
                <Route path="/referrals" element={<ReferralsPage />} />
              </Route>
              <Route element={<PermissionGuard permission="admission.view" />}>
                <Route path="/admissions" element={<AdmissionsPage />} />
              </Route>
              <Route
                element={<PermissionGuard permission="residential.view" />}
              >
                <Route path="/residential" element={<ResidentialPage />} />
              </Route>
              <Route
                element={
                  <PermissionGuard
                    permission={["assessment.view", "risk.view"]}
                  />
                }
              >
                <Route path="/assessments" element={<AssessmentsPage />} />
              </Route>
              <Route
                element={
                  <PermissionGuard
                    permission={[
                      "therapy.view",
                      "treatment_plan.view",
                      "case_management.view",
                      "programme.view",
                      "family.view",
                    ]}
                  />
                }
              >
                <Route
                  path="/rehabilitation"
                  element={<RehabilitationPage />}
                />
              </Route>
              <Route element={<PermissionGuard permission="clinical.view" />}>
                <Route path="/clinical" element={<ClinicalPage />} />
              </Route>
              <Route element={<PermissionGuard permission="nursing.view" />}>
                <Route path="/nursing" element={<NursingPage />} />
              </Route>
              <Route element={<PermissionGuard permission="lab.view" />}>
                <Route path="/laboratory" element={<LaboratoryPage />} />
              </Route>
              <Route element={<PermissionGuard permission="lab.view" />}>
                <Route path="/toxicology" element={<ToxicologyPage />} />
              </Route>
              <Route element={<PermissionGuard permission="medication.view" />}>
                <Route path="/medication" element={<MedicationPage />} />
              </Route>
              <Route element={<PermissionGuard permission="pharmacy.view" />}>
                <Route path="/pharmacy" element={<PharmacyPage />} />
              </Route>

              
              <Route element={<PermissionGuard permission="billing.view" />}><Route path="/billing/*" element={<BillingPage />} /></Route>
              <Route element={<PermissionGuard permission="inventory.view" />}><Route path="/inventory/*" element={<InventoryPage />} /></Route>
              <Route element={<PermissionGuard permission="discharge.view" />}><Route path="/discharge/*" element={<DischargePage />} /></Route>
              <Route element={<PermissionGuard permission="reporting.view" />}><Route path="/reporting/*" element={<ReportingPage />} /></Route>
              <Route element={<PermissionGuard permission="compliance.view" />}><Route path="/compliance/*" element={<CompliancePage />} /></Route>
              <Route element={<PermissionGuard permission="staff.view" />}><Route path="/staff/*" element={<StaffPage />} /></Route>

              <Route element={<PermissionGuard permission="users.manage" />}>
                <Route path="/administration/users" element={<UsersPage />} />
                <Route
                  path="/administration/users/new"
                  element={<UserFormPage />}
                />
              </Route>
              <Route element={<PermissionGuard permission="roles.manage" />}>
                <Route path="/administration/roles" element={<RolesPage />} />
              </Route>
              <Route
                element={<PermissionGuard permission="departments.manage" />}
              >
                <Route
                  path="/administration/departments"
                  element={<DepartmentsPage />}
                />
              </Route>
              <Route element={<PermissionGuard permission="audit.view" />}>
                <Route path="/administration/audit" element={<AuditPage />} />
              </Route>
              <Route element={<PermissionGuard permission="settings.manage" />}>
                <Route
                  path="/administration/settings"
                  element={<SettingsPage />}
                />
              </Route>
              <Route
                path="*"
                element={
                  <div>
                    <h1>Page not found</h1>
                    <p>Use the navigation to return to your workspace.</p>
                  </div>
                }
              />
            </Route>
          </Route>
        </Route>
      </Routes>
    </Suspense>
  );
}
