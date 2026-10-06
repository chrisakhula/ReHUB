import type { Resource } from "../care/types";

export const inventoryResources: Resource[] = [
  {
    path: "/inventory/items",
    title: "Store Items",
    permission: "inventory.view",
    columns: [
      { key: "code", label: "Item Code" },
      { key: "name", label: "Item Name" },
      { key: "category", label: "Category" },
      { key: "current_stock", label: "Current Stock" },
      { key: "unit_of_measure", label: "Unit" }
    ],
    fields: [
      { name: "code", label: "Item Code", type: "text", required: true },
      { name: "name", label: "Item Name", type: "text", required: true },
      { name: "category", label: "Category", type: "select", options: ["MEDICAL", "FOOD", "CLEANING", "OFFICE", "MAINTENANCE"], required: true },
      { name: "unit_of_measure", label: "Unit of Measure", type: "text", required: true },
      { name: "reorder_level", label: "Reorder Level", type: "number" },
      { name: "is_active", label: "Active", type: "select", options: ["true", "false"] }
    ]
  },
  {
    path: "/inventory/suppliers",
    title: "Suppliers",
    permission: "inventory.view",
    columns: [
      { key: "name", label: "Name" },
      { key: "contact_person", label: "Contact Person" },
      { key: "phone", label: "Phone" }
    ],
    fields: [
      { name: "name", label: "Supplier Name", type: "text", required: true },
      { name: "contact_person", label: "Contact Person", type: "text" },
      { name: "phone", label: "Phone", type: "text" },
      { name: "email", label: "Email", type: "text" },
      { name: "address", label: "Address", type: "textarea" },
      { name: "is_active", label: "Active", type: "select", options: ["true", "false"] }
    ]
  },
  {
    path: "/inventory/orders",
    title: "Purchase Orders",
    permission: "inventory.view",
    columns: [
      { key: "order_number", label: "Order Number" },
      { key: "order_date", label: "Date" },
      { key: "status", label: "Status" },
      { key: "total_amount", label: "Total Amount" }
    ],
    fields: [
      { name: "supplier_id", label: "Supplier", type: "lookup", source: "/inventory/suppliers", required: true },
      { name: "order_number", label: "Order Number", type: "text", required: true },
      { name: "order_date", label: "Order Date", type: "date", required: true },
      { name: "status", label: "Status", type: "select", options: ["DRAFT", "APPROVED", "ORDERED", "RECEIVED", "CANCELLED"] },
      { name: "total_amount", label: "Total Amount", type: "number" }
    ],
    statusOptions: ["DRAFT", "APPROVED", "ORDERED", "RECEIVED", "CANCELLED"]
  },
  {
    path: "/inventory/transactions",
    title: "Stock Transactions",
    permission: "inventory.view",
    columns: [
      { key: "created_at", label: "Date" },
      { key: "item_id", label: "Item" },
      { key: "transaction_type", label: "Type" },
      { key: "quantity", label: "Quantity" }
    ],
    fields: [
      { name: "item_id", label: "Store Item", type: "lookup", source: "/inventory/items", required: true },
      { name: "transaction_type", label: "Transaction Type", type: "select", options: ["RECEIPT", "ISSUE", "ADJUSTMENT", "RETURN"], required: true },
      { name: "quantity", label: "Quantity", type: "number", required: true },
      { name: "batch_number", label: "Batch Number", type: "text" },
      { name: "expiry_date", label: "Expiry Date", type: "date" },
      { name: "reference", label: "Reference (PO #, etc.)", type: "text" },
      { name: "notes", label: "Notes", type: "textarea" }
    ]
  }
];
