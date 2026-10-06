import { CareWorkspace } from "../care/CareWorkspace";
import { inventoryResources } from "./resources";

export function InventoryPage() {
  return (
    <CareWorkspace
      title="Inventory workspace"
      description="Manage inventory operations and records."
      resources={inventoryResources}
    />
  );
}
