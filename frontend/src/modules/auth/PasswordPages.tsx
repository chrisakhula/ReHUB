import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Alert, Button, Form } from "react-bootstrap";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ApiError, save } from "../../api/client";
import { useAuth } from "../../auth/AuthProvider";
import { FormField } from "../../components/FormField";
import { ErrorNotice } from "../../components/Common";
import { passwordSchema } from "../../schemas/auth";

const resetRequestSchema = z.object({ email: z.email() });
const resetSchema = z.object({
  new_password: z.string().min(12, "Use at least 12 characters").max(128),
});
export function ForgotPasswordPage() {
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const form = useForm<z.infer<typeof resetRequestSchema>>({
    resolver: zodResolver(resetRequestSchema),
  });
  return (
    <main className="auth-single">
      <h1>Reset your password</h1>
      <p>Enter your institutional email address.</p>
      <ErrorNotice error={error} />
      {message && <Alert variant="success">{message}</Alert>}
      <Form
        noValidate
        onSubmit={form.handleSubmit(async (data) => {
          try {
            setMessage(
              (await save<{ message: string }>("/auth/request-reset", data))
                .message,
            );
            setError("");
          } catch (e) {
            setError(String(e));
          }
        })}
      >
        <FormField
          label="Email address"
          type="email"
          registration={form.register("email")}
          error={form.formState.errors.email?.message}
        />
        <Button type="submit" disabled={form.formState.isSubmitting}>
          Send reset link
        </Button>
      </Form>
      <Link className="d-block mt-3" to="/login">
        Back to sign in
      </Link>
    </main>
  );
}
export function ResetPasswordPage() {
  const [token] = useState(() => {
    const value = new URLSearchParams(window.location.hash.slice(1)).get(
      "token",
    );
    window.history.replaceState(null, "", window.location.pathname);
    return value;
  });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const form = useForm<z.infer<typeof resetSchema>>({
    resolver: zodResolver(resetSchema),
  });
  return (
    <main className="auth-single">
      <h1>Choose a new password</h1>
      <ErrorNotice
        error={
          error ||
          (!token ? "Open the complete link from your reset email." : "")
        }
      />
      {message && <Alert variant="success">{message}</Alert>}
      <Form
        noValidate
        onSubmit={form.handleSubmit(async (data) => {
          try {
            setMessage(
              (
                await save<{ message: string }>("/auth/reset-password", {
                  ...data,
                  token,
                })
              ).message,
            );
          } catch (e) {
            setError(String(e));
          }
        })}
      >
        <FormField
          label="New password"
          type="password"
          autoComplete="new-password"
          registration={form.register("new_password")}
          error={form.formState.errors.new_password?.message}
        />
        <p className="text-secondary small">Use at least 12 characters.</p>
        <Button
          type="submit"
          disabled={!token || !!message || form.formState.isSubmitting}
        >
          Update password
        </Button>
      </Form>
      <Link className="d-block mt-3" to="/login">
        Back to sign in
      </Link>
    </main>
  );
}
export function ChangePasswordPage() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const temporaryPasswordRequired = !!auth.user?.force_password_change;
  const form = useForm<z.infer<typeof passwordSchema>>({
    resolver: zodResolver(passwordSchema),
  });
  return (
    <main className="auth-single">
      <div className="eyebrow">Account security</div>
      <h1>Change your password</h1>
      <p className="text-secondary mb-2">
        Signed in as <strong>{auth.user?.email}</strong>
      </p>
      <p>
        {temporaryPasswordRequired
          ? "Enter the temporary password you used to sign in, then choose a personal password."
          : "Changing your password signs out all sessions."}
      </p>
      <ErrorNotice error={error} />
      <Form
        noValidate
        aria-busy={form.formState.isSubmitting || signingOut}
        onSubmit={form.handleSubmit(async (data) => {
          setError("");
          try {
            await save("/auth/change-password", data);
            auth.clear();
            navigate("/login");
          } catch (e) {
            if (
              e instanceof ApiError &&
              e.status === 400 &&
              e.message === "Current password is incorrect"
            ) {
              form.setError(
                "current_password",
                {
                  type: "server",
                  message: temporaryPasswordRequired
                    ? "Enter the temporary password you used to sign in. Replace any old password filled in by your browser."
                    : "Enter the password you used to sign in to this account.",
                },
                { shouldFocus: true },
              );
            } else {
              setError(
                e instanceof Error ? e.message : "Password update failed.",
              );
            }
          }
        })}
      >
        <FormField
          label="Current password"
          type={showCurrentPassword ? "text" : "password"}
          autoComplete="current-password"
          registration={form.register("current_password")}
          error={form.formState.errors.current_password?.message}
          help={
            temporaryPasswordRequired
              ? "Use your temporary sign-in password here. Your previous password no longer works after a reset."
              : "Use the password for the account shown above."
          }
        />
        <Form.Check
          id="show-current-password"
          className="mb-3"
          type="checkbox"
          label="Show current password"
          checked={showCurrentPassword}
          onChange={(event) => setShowCurrentPassword(event.target.checked)}
        />
        <FormField
          label="New password"
          type="password"
          autoComplete="new-password"
          registration={form.register("new_password")}
          error={form.formState.errors.new_password?.message}
        />
        <p className="text-secondary small">
          Use at least 12 characters. Choose a password you do not use
          elsewhere.
        </p>
        <div className="d-flex flex-wrap gap-2">
          <Button
            type="submit"
            disabled={form.formState.isSubmitting || signingOut}
          >
            {form.formState.isSubmitting
              ? "Updating password…"
              : "Update password"}
          </Button>
          <Button
            type="button"
            variant="outline-secondary"
            disabled={form.formState.isSubmitting || signingOut}
            onClick={async () => {
              setSigningOut(true);
              setError("");
              try {
                await auth.logout();
                navigate("/login");
              } catch (e) {
                setError(e instanceof Error ? e.message : "Sign out failed.");
              } finally {
                setSigningOut(false);
              }
            }}
          >
            {signingOut ? "Signing out…" : "Sign out"}
          </Button>
        </div>
      </Form>
    </main>
  );
}
