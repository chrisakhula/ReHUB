import { z } from "zod";
export const userSchema = z.object({
  full_name: z.string().trim().min(2).max(150),
  email: z.email(),
  password: z.string().max(128),
  department_id: z.string(),
  role_ids: z.array(z.string()),
  permission_ids: z.array(z.string()),
  active: z.boolean(),
  force_password_change: z.boolean(),
  reason: z.string().max(500),
});
export function userFormSchema(editing: boolean) {
  return userSchema.superRefine((data, context) => {
    if (!editing && data.password.length < 12) {
      context.addIssue({
        code: "custom",
        path: ["password"],
        message: "Use at least 12 characters",
      });
    }
    if (editing && data.reason.trim().length < 3) {
      context.addIssue({
        code: "custom",
        path: ["reason"],
        message: "Provide a reason for this change",
      });
    }
  });
}
export const roleSchema = z.object({
  name: z.string().trim().min(2).max(100),
  description: z.string().max(500),
  permission_ids: z.array(z.string()),
  reason: z.string().min(3).max(500),
});
export const departmentSchema = z.object({
  name: z.string().trim().min(2).max(100),
  description: z.string().max(500),
  active: z.boolean(),
});
export const facilitySchema = z.object({
  name: z.string().min(2).max(150),
  system_name: z.string().min(2).max(150),
  short_name: z.string().min(2).max(30),
  contact_email: z.union([z.email(), z.literal("")]),
  phone: z.string().max(30),
  address: z.string().max(1000),
  logo_url: z.union([z.url().startsWith("https://"), z.literal("")]),
});
