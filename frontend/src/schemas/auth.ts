import { z } from "zod";
export const loginSchema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password").max(128),
});
export const passwordSchema = z.object({
  current_password: z.string().min(1),
  new_password: z.string().min(12, "Use at least 12 characters").max(128),
});
