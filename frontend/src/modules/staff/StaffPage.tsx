import { CareWorkspace } from "../care/CareWorkspace";
import { staffResources } from "./resources";

export function StaffPage() {
  return (
    <CareWorkspace
      title="Staff workspace"
      description="Manage staff profiles, shifts, and credentials."
      resources={staffResources}
    />
  );
}
