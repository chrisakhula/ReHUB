import { CareWorkspace } from "../care/CareWorkspace";
import { residentialResources } from "./resources";

export function ResidentialPage() {
  return (
    <CareWorkspace
      title="Residential workspace"
      description="Manage residential operations and records."
      resources={residentialResources}
    />
  );
}
