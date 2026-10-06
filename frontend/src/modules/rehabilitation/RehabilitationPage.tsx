import { useAuth } from "../../auth/AuthProvider";
import { ProgrammeSchedule } from "./ProgrammeSchedule";
import { CareWorkspace } from "../care/CareWorkspace";
import { rehabResources } from "./resources";
export function RehabilitationPage() {
  return (
    <CareWorkspace
      title="Rehabilitation & case management"
      description="Manage versioned treatment plans, counselling, groups, programme participation and family work."
      resources={rehabResources}
    >
      {useAuth().can("programme.view") && <ProgrammeSchedule />}
    </CareWorkspace>
  );
}
