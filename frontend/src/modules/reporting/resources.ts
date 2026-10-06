import type { Resource } from "../care/types";

export const reportingResources: Resource[] = [
  {
    path: "/reporting",
    title: "Reporting Records",
    permission: "reporting.view",
    columns: [{ key: "id", label: "Identifier" }],
  }
];
