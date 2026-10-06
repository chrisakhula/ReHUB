import { CareWorkspace } from "../care/CareWorkspace";
import { complianceResources } from "./resources";

export function CompliancePage() {
  return (
    <CareWorkspace
      title="Compliance & Quality"
      description="Manage facility licences, audits, and compliance records."
      resources={complianceResources}
    />
  );
}
