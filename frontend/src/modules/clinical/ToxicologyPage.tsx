import { CareWorkspace } from "../care/CareWorkspace";
import { toxicologyResources } from "./resources";
export function ToxicologyPage() {
  return (
    <CareWorkspace
      title="Toxicology"
      description="Record tests by substance and inspect the client's longitudinal testing history."
      resources={toxicologyResources}
    />
  );
}
