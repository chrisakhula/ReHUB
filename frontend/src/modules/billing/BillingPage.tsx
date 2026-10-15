import { useState } from "react";
import { CareWorkspace } from "../care/CareWorkspace";
import { billingResources } from "./resources";
import { MpesaReconciliationWorkspace } from "./MpesaReconciliationWorkspace";

export function BillingPage() {
  const [activeTab, setActiveTab] = useState<"records" | "mpesa">("records");

  return (
    <div>
      <div className="bg-white border-bottom px-4 pt-3 pb-0 mb-3">
        <ul className="nav nav-tabs border-0">
          <li className="nav-item">
            <button
              className={`nav-link ${activeTab === "records" ? "active fw-bold text-primary" : "text-secondary"}`}
              onClick={() => setActiveTab("records")}
            >
              Billing Records & Fee Schedules
            </button>
          </li>
          <li className="nav-item">
            <button
              className={`nav-link ${activeTab === "mpesa" ? "active fw-bold text-primary" : "text-secondary"}`}
              onClick={() => setActiveTab("mpesa")}
            >
              M-Pesa Reconciliation & STK Push
            </button>
          </li>
        </ul>
      </div>

      {activeTab === "records" ? (
        <CareWorkspace
          title="Billing workspace"
          description="Manage invoices, fee catalogues, payers and payment records."
          resources={billingResources}
        />
      ) : (
        <MpesaReconciliationWorkspace />
      )}
    </div>
  );
}

