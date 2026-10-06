import { CareWorkspace } from "../care/CareWorkspace";
import { labResources } from "./resources";
export function LaboratoryPage() {
  return (
    <CareWorkspace
      title="Laboratory & investigations"
      description="Request external investigations, record results and preserve clinician review and PDF history."
      resources={labResources}
    />
  );
}
