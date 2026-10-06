import { CareWorkspace } from "../care/CareWorkspace";
import { dischargeResources } from "./resources";

export function DischargePage() {
  return (
    <CareWorkspace
      title="Discharge workspace"
      description="Manage discharge operations and records."
      resources={dischargeResources}
    />
  );
}
