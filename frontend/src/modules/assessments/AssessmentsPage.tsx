import { useAuth } from "../../auth/AuthProvider";
import { CareWorkspace } from "../care/CareWorkspace";
import { assessmentResources, instrumentResource } from "./resources";
import { ScorePanel } from "./ScorePanel";
export function AssessmentsPage() {
  return (
    <CareWorkspace
      title="Assessments & risk"
      description="Record substance history, biopsychosocial assessments, instrument scores and risk interventions."
      resources={[...assessmentResources, instrumentResource]}
    >
      {useAuth().can("assessment.view") && <ScorePanel />}
    </CareWorkspace>
  );
}
