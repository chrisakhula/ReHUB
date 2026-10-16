import { useState } from "react";
import { CareWorkspace } from "../care/CareWorkspace";
import { billingResources } from "./resources";
import { MpesaReconciliationWorkspace } from "./MpesaReconciliationWorkspace";
import { ClientFinanceWorkspace } from "./ClientFinanceWorkspace";

export function BillingPage() {
  const [activeTab, setActiveTab] = useState<"records" | "statements" | "mpesa">("records");

  return (
    <div>
      <div className="bg-white border-bottom px-4 pt-3 pb-0 mb-3">
        <ul className="nav nav-tabs border-0">
          <li className="nav-item">
            <button
              className={`nav-link ${activeTab === "statements" ? "active fw-bold text-primary" : "text-secondary"}`}
              onClick={() => setActiveTab("statements")}
            >
              <i className="bi bi-wallet2 me-1"></i> Client Accounts & Statements
            </button>
          </li>
          <li className="nav-item">
            <button
              className={`nav-link ${activeTab === "records" ? "active fw-bold text-primary" : "text-secondary"}`}
              onClick={() => setActiveTab("records")}
            >
              <i className="bi bi-folder2-open me-1"></i> Billing Records & Lifecycles
            </button>
          </li>
          <li className="nav-item">
            <button
              className={`nav-link ${activeTab === "mpesa" ? "active fw-bold text-primary" : "text-secondary"}`}
              onClick={() => setActiveTab("mpesa")}
            >
              <i className="bi bi-phone me-1"></i> M-Pesa Reconciliation & STK Push
            </button>
          </li>
        </ul>
      </div>

      {activeTab === "statements" ? (
        <ClientFinanceWorkspace />
      ) : activeTab === "records" ? (
        <CareWorkspace
          title="Billing workspace"
          description="Manage client estimates, financial agreements, package billing, payment plans, refunds, and clearances."
          resources={billingResources}
        />
      ) : (
        <MpesaReconciliationWorkspace />
      )}
    </div>
  );
}

