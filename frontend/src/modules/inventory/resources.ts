import type { Resource } from "../care/types";

export const inventoryResources: Resource[] = [
  {
    path: "/inventory/items",
    title: "Inventory Items",
    permission: "inventory.view",
    columns: [
      { key: "name", label: "Item Name" },
      { key: "category", label: "Category" },
      { key: "current_stock", label: "Stock Level" },
      { key: "unit_of_measure", label: "Unit" }
    ],
    fields: [
      { name: "name", label: "Item Name", type: "text", required: true },
      { name: "category", label: "Category", type: "select", options: ["medication", "consumable", "equipment", "food", "office"], required: true },
      { name: "unit_of_measure", label: "Unit of Measure", type: "text", required: true },
      { name: "current_stock", label: "Current Stock", type: "number", required: true },
      { name: "minimum_stock_level", label: "Minimum Stock", type: "number" }
    ]
  }
];
