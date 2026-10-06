import { CareWorkspace } from "../care/CareWorkspace";
import { billingResources } from "./resources";

export function BillingPage() {
  return (
    <CareWorkspace
      title="Billing workspace"
      description="Manage billing operations and records."
      resources={billingResources}
    />
  );
}
