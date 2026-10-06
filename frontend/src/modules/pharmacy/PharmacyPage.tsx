import { useQuery } from "@tanstack/react-query";
import { Tabs, Tab } from "react-bootstrap";
import { api } from "../../api/client";
import { PageHeader, ErrorNotice } from "../../components/Common";
import { ResourcePanel, RecordDetails } from "../care/ResourcePanel";
import {
  check,
  choice,
  date,
  lookup,
  number,
  reason,
  text,
} from "../care/fields";
import type { Field, Resource, Values } from "../care/types";

const catalogue: Field[] = [
  text("generic_name", "Generic name", true),
  text("brand_name", "Brand name"),
  text("formulation", "Formulation", true),
  text("strength", "Strength", true),
  text("dose_unit", "Dose / stock unit", true),
  { ...number("reorder_level", "Reorder level", false, 0), default: 0 },
  check("active", "Active medication", undefined, true),
];
const resources: Resource[] = [
  {
    title: "Stock count history",
    path: "/pharmacy/counts",
    permission: "pharmacy.view",
    columns: [
      { key: "batch_id", label: "Batch" },
      { key: "expected_quantity", label: "Expected" },
      { key: "counted_quantity", label: "Counted" },
      { key: "variance", label: "Variance" },
      { key: "created_at", label: "Counted at" },
    ],
  },
  {
    title: "Drug batches",
    path: "/pharmacy/batches",
    permission: "pharmacy.view",
    writePermission: "pharmacy.manage",
    fields: [
      lookup(
        "medication_id",
        "Medication",
        "/medication/catalogue",
        true,
        undefined,
        ["generic_name", "strength", "dose_unit"],
      ),
      lookup("supplier_id", "Supplier", "/pharmacy/suppliers", false),
      text("batch_number", "Batch number", true),
      date("expiry_date", "Expiry date", true),
      number("quantity", "Quantity received", true, 0.001),
      text("unit", "Stock unit (match catalogue)", true),
      text("receipt_reference", "Purchase receipt reference", true),
    ],
    columns: [
      { key: "batch_number", label: "Batch" },
      { key: "medication_id", label: "Medication" },
      { key: "expiry_date", label: "Expiry" },
      { key: "quantity", label: "Stock" },
      { key: "unit", label: "Unit" },
    ],
    actions: [
      {
        label: "Record stock movement",
        permission: "pharmacy.dispense",
        path: () => "/pharmacy/movements",
        fields: [
          text("batch_id", "Batch ID", true),
          choice("movement_type", "Movement", [
            "DISPENSE",
            "WARD_ISSUE",
            "WARD_RETURN",
            "WARD_USE",
            "RETURN",
            "ADJUST_IN",
            "ADJUST_OUT",
            "DAMAGED",
            "EXPIRED",
          ]),
          number("quantity", "Quantity", true, 0.001),
          lookup(
            "prescription_id",
            "Active prescription (for dispensing)",
            "/medication/prescriptions?status=ACTIVE",
            false,
            undefined,
            ["generic_name", "admission_id"],
          ),
          text("location", "Ward location (for ward movements)"),
          text("reference", "Reference"),
          reason,
        ],
        defaults: (r) => ({ batch_id: r.id }),
      },
      {
        label: "Reconcile stock count",
        permission: "pharmacy.manage",
        path: () => "/pharmacy/counts",
        fields: [
          text("batch_id", "Batch ID", true),
          number("counted_quantity", "Counted quantity", true, 0),
          reason,
        ],
        defaults: (r) => ({ batch_id: r.id, counted_quantity: r.quantity }),
      },
    ],
  },
  {
    title: "Medication catalogue",
    path: "/medication/catalogue",
    permission: "medication.view",
    writePermission: "pharmacy.manage",
    fields: catalogue,
    columns: [
      { key: "generic_name", label: "Generic name" },
      { key: "brand_name", label: "Brand" },
      { key: "strength", label: "Strength" },
      { key: "formulation", label: "Form" },
      { key: "active", label: "Active" },
    ],
    actions: [
      {
        label: "Update catalogue entry",
        permission: "pharmacy.manage",
        path: (r) => `/medication/catalogue/${r.id}`,
        method: "PUT",
        fields: catalogue,
      },
    ],
  },
  {
    title: "Suppliers",
    path: "/pharmacy/suppliers",
    permission: "pharmacy.view",
    writePermission: "pharmacy.manage",
    fields: [
      text("name", "Supplier name", true),
      text("phone", "Phone number"),
      text("email", "Email address"),
      check("active", "Active supplier", undefined, true),
    ],
    columns: [
      { key: "name", label: "Supplier" },
      { key: "phone", label: "Phone" },
      { key: "email", label: "Email" },
      { key: "active", label: "Active" },
    ],
  },
  {
    title: "Stock movements",
    path: "/pharmacy/movements",
    permission: "pharmacy.view",
    columns: [
      { key: "movement_type", label: "Movement" },
      { key: "quantity", label: "Quantity" },
      { key: "resulting_quantity", label: "Pharmacy balance" },
      { key: "location", label: "Ward" },
      { key: "reference", label: "Reference" },
      { key: "created_at", label: "Recorded" },
    ],
  },
  {
    title: "Ward stock",
    path: "/pharmacy/ward-stock",
    permission: "pharmacy.view",
    columns: [
      { key: "location", label: "Ward" },
      { key: "batch_id", label: "Batch" },
      { key: "quantity", label: "Quantity" },
    ],
  },
];
export function PharmacyPage() {
  const alerts = useQuery({
    queryKey: ["pharmacy-alerts"],
    queryFn: () => api<Values>("/pharmacy/alerts"),
  });
  return (
    <>
      <PageHeader
        title="Pharmacy"
        description="Batch-level receipts, dispensing, ward stock, counts and expiry monitoring."
      />
      <ErrorNotice error={alerts.error} />
      <details className="card card-body mb-4">
        <summary>Stock & expiry alerts</summary>
        {alerts.data && <RecordDetails record={alerts.data} />}
      </details>
      <Tabs
        defaultActiveKey={resources[0].path}
        className="mb-4"
        mountOnEnter
        unmountOnExit
      >
        {resources.map((r) => (
          <Tab eventKey={r.path} title={r.title} key={r.path}>
            <ResourcePanel resource={r} />
          </Tab>
        ))}
      </Tabs>
    </>
  );
}
