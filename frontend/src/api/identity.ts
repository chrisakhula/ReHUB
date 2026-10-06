import { api, save } from "./client";
import type {
  Department,
  Facility,
  Page,
  Permission,
  Role,
  User,
} from "../types/identity";

export const identityApi = {
  login: (email: string, password: string) =>
    save<User>("/auth/login", { email, password }),
  me: () => api<User>("/auth/me"),
  refresh: () => api<User>("/auth/refresh", { method: "POST" }, false),
  logout: () => api("/auth/logout", { method: "POST" }),
  roles: () => api<Page<Role>>("/roles?page_size=100"),
  permissions: () => api<Page<Permission>>("/permissions?page_size=100"),
  departments: () => api<Page<Department>>("/departments?page_size=100"),
  settings: () => api<Facility>("/settings"),
};
