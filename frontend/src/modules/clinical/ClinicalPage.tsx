import { CareWorkspace } from "../care/CareWorkspace";
import { clinicalResources } from "./resources";
export function ClinicalPage() {
  return (
    <CareWorkspace
      title="Clinical care"
      description="Clinical encounters, problems, allergies, vital signs and medical orders."
      resources={clinicalResources}
    />
  );
}
