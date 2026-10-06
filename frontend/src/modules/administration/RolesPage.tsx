import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Form, Table } from "react-bootstrap";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api, save } from "../../api/client";
import { identityApi } from "../../api/identity";
import type { Page, Role } from "../../types/identity";
import { roleSchema } from "../../schemas/administration";
import { useAuth } from "../../auth/AuthProvider";
import {
  Empty,
  ErrorNotice,
  Loading,
  PageHeader,
  Pagination,
} from "../../components/Common";
import { FormField } from "../../components/FormField";

export function RolesPage() {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [editing, setEditing] = useState<Role | "new" | null>(null);
  const [error, setError] = useState("");
  const cache = useQueryClient();
  const auth = useAuth();
  const query = useQuery({
    queryKey: ["roles", page, q],
    queryFn: () =>
      api<Page<Role>>(`/roles?page=${page}&q=${encodeURIComponent(q)}`),
  });
  const permissions = useQuery({
    queryKey: ["permissions-select"],
    queryFn: identityApi.permissions,
  });
  const form = useForm<z.infer<typeof roleSchema>>({
    resolver: zodResolver(roleSchema),
    defaultValues: {
      name: "",
      description: "",
      permission_ids: [],
      reason: "",
    },
  });
  const edit = (role: Role | "new") => {
    setEditing(role);
    setError("");
    form.reset(
      role === "new"
        ? { name: "", description: "", permission_ids: [], reason: "" }
        : {
            name: role.name,
            description: role.description,
            permission_ids: role.permissions.map((p) => p.id),
            reason: "",
          },
    );
  };
  return (
    <>
      <PageHeader
        title="Roles & permissions"
        description="Define explicit access. Administrative roles do not inherit clinical privileges."
        action={<Button onClick={() => edit("new")}>Create role</Button>}
      />
      <ErrorNotice error={error || query.error || permissions.error} />
      {editing && (
        <section className="card mb-4">
          <div className="card-header">
            <h2>
              {editing === "new" ? "Create role" : `Edit ${editing.name}`}
            </h2>
          </div>
          <div className="card-body">
            <Form
              noValidate
              onSubmit={form.handleSubmit(async (values) => {
                try {
                  await save(
                    editing === "new" ? "/roles" : `/roles/${editing.id}`,
                    values,
                    editing === "new" ? "POST" : "PUT",
                  );
                  setEditing(null);
                  await cache.invalidateQueries();
                } catch (e) {
                  setError(String(e));
                }
              })}
            >
              <div className="row">
                <div className="col-lg-5">
                  <FormField
                    label="Role name"
                    required
                    registration={form.register("name")}
                    error={form.formState.errors.name?.message}
                  />
                  <FormField
                    label="Description"
                    registration={form.register("description")}
                    error={form.formState.errors.description?.message}
                  />
                  <FormField
                    label="Reason for change"
                    required
                    registration={form.register("reason")}
                    error={form.formState.errors.reason?.message}
                  />
                </div>
                <fieldset className="col-lg-7">
                  <legend className="fs-6 fw-semibold">
                    Permission assignments
                  </legend>
                  <p className="small text-secondary">
                    Future module permissions are reserved and do not activate
                    those modules.
                  </p>
                  <div className="permission-grid">
                    {permissions.data?.items.map((p) => (
                      <Form.Check
                        key={p.id}
                        id={`role-perm-${p.id}`}
                        label={p.code}
                        title={p.description}
                        value={p.id}
                        {...form.register("permission_ids")}
                        disabled={!auth.can(p.code)}
                      />
                    ))}
                  </div>
                </fieldset>
              </div>
              <div className="form-actions">
                <Button
                  type="submit"
                  disabled={
                    form.formState.isSubmitting ||
                    permissions.isPending ||
                    !!permissions.error
                  }
                >
                  Save role
                </Button>
                <Button
                  variant="outline-secondary"
                  onClick={() => setEditing(null)}
                >
                  Cancel
                </Button>
              </div>
            </Form>
          </div>
        </section>
      )}
      <section className="card">
        <div className="table-toolbar">
          <Form.Group controlId="role-search">
            <Form.Label>Search roles</Form.Label>
            <Form.Control
              value={q}
              placeholder="Role name"
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
            />
          </Form.Group>
        </div>
        {query.isPending ? (
          <Loading />
        ) : query.data?.items.length ? (
          <div className="table-responsive">
            <Table hover className="mb-0">
              <thead>
                <tr>
                  <th>Role</th>
                  <th>Permissions</th>
                  <th>Description</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {query.data.items.map((role) => (
                  <tr key={role.id}>
                    <td>
                      <strong>{role.name}</strong>
                    </td>
                    <td>{role.permissions.length} assigned</td>
                    <td>{role.description}</td>
                    <td>
                      <Button
                        size="sm"
                        variant="outline-secondary"
                        onClick={() => edit(role)}
                        disabled={role.permissions.some(
                          (p) => !auth.can(p.code),
                        )}
                      >
                        Edit
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        ) : (
          <Empty>No roles match your search.</Empty>
        )}
        <Pagination
          page={page}
          total={query.data?.meta.total ?? 0}
          onChange={setPage}
        />
      </section>
    </>
  );
}
