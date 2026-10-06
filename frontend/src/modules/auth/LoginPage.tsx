import { useState } from "react";
import { Navigate, Link } from "react-router-dom";
import { Button, Form } from "react-bootstrap";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../../auth/AuthProvider";
import { identityApi } from "../../api/identity";
import { loginSchema } from "../../schemas/auth";
import { FormField } from "../../components/FormField";
import { ErrorNotice } from "../../components/Common";

export function LoginPage() {
  const auth = useAuth();
  const [error, setError] = useState("");
  const settings = useQuery({
    queryKey: ["settings"],
    queryFn: identityApi.settings,
  });
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
  });
  if (auth.user) return <Navigate to="/" replace />;
  return (
    <main className="login-layout">
      <section className="login-context">
        <div className="brand-mark">
          {settings.data?.logo_url ? (
            <img src={settings.data.logo_url} alt="Institution logo" />
          ) : (
            "ARS"
          )}
        </div>
        <h1>
          Rehabilitation
          <br />
          Management System
        </h1>
        <p>
          A secure workspace for coordinated care and institutional
          administration.
        </p>
        <div className="login-principles">
          <div>
            <i className="bi bi-shield-check" aria-hidden="true" /> Controlled
            access
          </div>
          <div>
            <i className="bi bi-journal-check" aria-hidden="true" /> Accountable
            records
          </div>
          <div>
            <i className="bi bi-building" aria-hidden="true" /> Connected
            administration
          </div>
        </div>
        <small>ARS RMS · Staff access only</small>
      </section>
      <section className="login-form-panel">
        <div className="login-form">
          <div className="eyebrow">Staff portal</div>
          <h2>Sign in</h2>
          <p className="text-secondary mb-4">
            Use your institutional account to continue.
          </p>
          <ErrorNotice error={error || auth.error} />
          <Form
            onSubmit={handleSubmit(async (values) => {
              setError("");
              try {
                await auth.login(values.email, values.password);
              } catch (e) {
                setError(e instanceof Error ? e.message : "Sign in failed");
              }
            })}
            noValidate
          >
            <FormField
              label="Email address"
              registration={register("email")}
              type="email"
              autoComplete="username"
              required
              error={errors.email?.message}
            />
            <FormField
              label="Password"
              registration={register("password")}
              type="password"
              autoComplete="current-password"
              required
              error={errors.password?.message}
            />
            <Button
              type="submit"
              className="w-100 mt-2"
              disabled={isSubmitting}
            >
              {isSubmitting ? "Signing in…" : "Sign in"}
            </Button>
          </Form>
          <Link to="/forgot-password" className="d-inline-block mt-3">
            Forgot your password?
          </Link>
          <div className="confidentiality">
            <i className="bi bi-lock" aria-hidden="true" /> Access is restricted
            to authorised staff. Activity is recorded for security and
            accountability.
          </div>
        </div>
      </section>
    </main>
  );
}
