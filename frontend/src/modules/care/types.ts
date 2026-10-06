export type Values = Record<string, unknown>;
export type Entity = Values & { id: string };
export interface Choice {
  value: string;
  label: string;
}
export interface Field {
  name: string;
  label: string;
  type?:
    | "text"
    | "textarea"
    | "number"
    | "checkbox"
    | "date"
    | "datetime-local"
    | "select"
    | "lookup"
    | "strings"
    | "array"
    | "object"
    | "file";
  required?: boolean;
  section?: string;
  options?: string[] | Choice[];
  source?: string;
  sourceKey?: string;
  labelKeys?: string[];
  fields?: Field[];
  default?: unknown;
  min?: number;
  max?: number;
  help?: string;
  accept?: string;
}
export interface Column {
  key: string;
  label: string;
}
export interface Action {
  label: string;
  permission: string;
  path: (record: Entity) => string;
  method?: string;
  fields: Field[];
  defaults?: (record: Entity) => Values;
  visible?: (record: Entity) => boolean;
  contextKeys?: string[];
}
export interface Resource {
  title: string;
  path: string;
  permission: string;
  writePermission?: string;
  fields?: Field[];
  columns: Column[];
  admissionScoped?: boolean;
  clientScoped?: boolean;
  defaults?: Values;
  actions?: Action[];
  statusOptions?: string[];
  sortOptions?: string[];
  transform?: (values: Values) => Values;
  historyPath?: (record: Entity) => string;
  readLinks?: {
    label: string;
    permission: string;
    path: (record: Entity) => string;
    visible?: (record: Entity) => boolean;
  }[];
}
export interface CareOption {
  id: string;
  client_id: string;
  client_name: string;
  admission_number: string;
  client_number: string;
  status: string;
}
export interface CareOptions {
  selected?: CareOption | null;
  admissions: CareOption[];
  staff: { id: string; full_name: string }[];
  meta: { page: number; page_size: number; total: number };
}
