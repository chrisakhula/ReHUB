export interface Permission {
  id: string;
  code: string;
  description: string;
}
export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: Permission[];
}
export interface User {
  id: string;
  email: string;
  full_name: string;
  active: boolean;
  force_password_change: boolean;
  department_id: string | null;
  facility_id: string;
  last_login: string | null;
  created_at: string;
  roles: Role[];
  direct_permissions: Permission[];
  permissions: string[];
}
export interface Department {
  id: string;
  name: string;
  description: string;
  active: boolean;
}
export interface Facility {
  name: string;
  system_name: string;
  short_name: string;
  contact_email: string | null;
  phone: string | null;
  address: string | null;
  logo_url: string | null;
}
export interface Page<T> {
  items: T[];
  meta: { page: number; page_size: number; total: number };
}
export interface AuditEvent {
  id: string;
  timestamp: string;
  action: string;
  entity: string;
  entity_id: string | null;
  user_id: string | null;
  ip_address: string | null;
  reason: string | null;
  previous_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
}
