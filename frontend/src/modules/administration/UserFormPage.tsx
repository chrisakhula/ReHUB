import { useState } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Form } from "react-bootstrap";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { identityApi } from "../../api/identity";
import { save } from "../../api/client";
import { userSchema, userFormSchema } from "../../schemas/administration";
import type { User } from "../../types/identity";
import { useAuth } from "../../auth/AuthProvider";
import { ErrorNotice, Loading, PageHeader } from "../../components/Common";
import { FormField } from "../../components/FormField";

export function UserFormPage() {
  const location = useLocation();
  const user = (location.state as { user?: User } | null)?.user;
  const navigate = useNavigate();
  const cache = useQueryClient();
  const auth = useAuth();
  const [error, setError] = useState("");
  const roles = useQuery({
    queryKey: ["roles-select"],
    queryFn: identityApi.roles,
  });
  const departments = useQuery({
    queryKey: ["departments-select"],
    queryFn: identityApi.departments,
  });
  const permissions = useQuery({
    queryKey: ["permissions-select"],
    queryFn: identityApi.permissions,
  });
  const form = useForm<z.infer<typeof userSchema>>({
    resolver: zodResolver(userFormSchema(!!user)),
    defaultValues: {
      full_name: user?.full_name ?? "",
      email: user?.email ?? "",
      password: "",
      department_id: user?.department_id ?? "",
      role_ids: user?.roles.map((r) => r.id) ?? [],
      permission_ids: user?.direct_permissions.map((p) => p.id) ?? [],
      active: user?.active ?? true,
      force_password_change: user?.force_password_change ?? true,
      reason: "",
    },
  });
  return (
    <>
      <PageHeader
        title={user ? "Edit staff account" : "Create staff account"}
        description="Assign only the access required for this staff member."
      />
      <Link to="/administration/users" className="d-inline-block mb-3">
        Back to users
      </Link>
      <ErrorNotice
        error={error || roles.error || departments.error || permissions.error}
      />
      {roles.isPending || departments.isPending || permissions.isPending ? (
        <Loading />
      ) : (
        <Form
          noValidate
          onSubmit={form.handleSubmit(async (data) => {
            const payload = {
              ...data,
              department_id: data.department_id || null,
            };
            try {
              await save(
                user ? `/users/${user.id}` : "/users",
                payload,
                user ? "PUT" : "POST",
              );
              await cache.invalidateQueries();
              if (user?.id === auth.user?.id) auth.clear();
              navigate("/administration/users");
            } catch (e) {
              setError(String(e));
            }
          })}
        >
          <div className="row g-4">
            <div className="col-lg-6">
              <fieldset className="card">
                <legend className="card-header">Staff details</legend>
                <div className="card-body">
                  <FormField
                    label="Full name"
                    required
                    registration={form.register("full_name")}
                    error={form.formState.errors.full_name?.message}
                  />
                  {!user ? (
                    <>
                      <FormField
                        label="Email address"
                        required
                        type="email"
                        registration={form.register("email")}
                        error={form.formState.errors.email?.message}
                      />
                      <FormField
                        label="Temporary password"
                        required
                        type="password"
                        autoComplete="new-password"
                        registration={form.register("password")}
                        error={form.formState.errors.password?.message}
                      />
                      <p className="small text-secondary">
                        At least 12 characters. The user must change it on first
                        sign in.
                      </p>
                    </>
                  ) : (
                    <p>{user.email}</p>
                  )}
                  <Form.Group controlId="department">
                    <Form.Label>Department</Form.Label>
                    <Form.Select {...form.register("department_id")}>
                      <option value="">Unassigned</option>
                      {departments.data?.items
                        .filter((d) => d.active)
                        .map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name}
                          </option>
                        ))}
                    </Form.Select>
                  </Form.Group>
                  {user && (
                    <div className="mt-3">
                      <Form.Check
                        id="active"
                        label="Account active"
                        {...form.register("active")}
                      />
                      <Form.Check
                        id="force-change"
                        label="Require password change"
                        {...form.register("force_password_change")}
                      />
                    </div>
                  )}
                </div>
              </fieldset>
            </div>
            <div className="col-lg-6">
              <fieldset className="card">
                <legend className="card-header">
                  Roles & explicit permissions
                </legend>
                <div className="card-body">
                  <p className="small text-secondary">
                    You can grant only permissions you currently hold.
                  </p>
                  {roles.data?.items.map((role) => (
                    <Form.Check
                      key={role.id}
                      id={`role-${role.id}`}
                      label={role.name}
                      value={role.id}
                      {...form.register("role_ids")}
                      disabled={role.permissions.some((p) => !auth.can(p.code))}
                    />
                  ))}
                  <details className="mt-3">
                    <summary>Explicit permissions</summary>
                    {permissions.data?.items.map((p) => (
                      <Form.Check
                        key={p.id}
                        id={`perm-${p.id}`}
                        label={p.code}
                        value={p.id}
                        disabled={!auth.can(p.code)}
                        {...form.register("permission_ids")}
                      />
                    ))}
                  </details>
                </div>
              </fieldset>
            </div>
          </div>
          {user && (
            <div className="mt-4">
              <FormField
                label="Reason for change"
                required
                registration={form.register("reason")}
                error={form.formState.errors.reason?.message}
              />
            </div>
          )}
          <div className="form-actions">
            <Button
              type="submit"
              disabled={
                form.formState.isSubmitting ||
                !!roles.error ||
                !!permissions.error ||
                !!departments.error
              }
            >
              {form.formState.isSubmitting
                ? "Saving…"
                : user
                  ? "Save changes"
                  : "Create user"}
            </Button>
            <Link
              to="/administration/users"
              className="btn btn-outline-secondary"
            >
              Cancel
            </Link>
          </div>
        </Form>
      )}
    </>
  );
}
