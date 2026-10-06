import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Form, Table } from "react-bootstrap";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api, save } from "../../api/client";
import type { Department, Page } from "../../types/identity";
import { departmentSchema } from "../../schemas/administration";
import {
  Empty,
  ErrorNotice,
  Loading,
  PageHeader,
  Pagination,
} from "../../components/Common";
import { FormField } from "../../components/FormField";

export function DepartmentsPage() {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [editing, setEditing] = useState<Department | "new" | null>(null);
  const [error, setError] = useState("");
  const cache = useQueryClient();
  const query = useQuery({
    queryKey: ["departments", page, q],
    queryFn: () =>
      api<Page<Department>>(
        `/departments?page=${page}&q=${encodeURIComponent(q)}`,
      ),
  });
  const form = useForm<z.infer<typeof departmentSchema>>({
    resolver: zodResolver(departmentSchema),
    defaultValues: { name: "", description: "", active: true },
  });
  const edit = (d: Department | "new") => {
    setEditing(d);
    form.reset(d === "new" ? { name: "", description: "", active: true } : d);
  };
  return (
    <>
      <PageHeader
        title="Departments"
        description="Maintain the institution’s staff organisation."
        action={<Button onClick={() => edit("new")}>Create department</Button>}
      />
      <ErrorNotice error={error || query.error} />
      {editing && (
        <section className="card mb-4">
          <div className="card-body">
            <Form
              onSubmit={form.handleSubmit(async (data) => {
                try {
                  await save(
                    editing === "new"
                      ? "/departments"
                      : `/departments/${editing.id}`,
                    data,
                    editing === "new" ? "POST" : "PUT",
                  );
                  setEditing(null);
                  setError("");
                  await cache.invalidateQueries();
                } catch (e) {
                  setError(String(e));
                }
              })}
              noValidate
            >
              <FormField
                label="Department name"
                required
                registration={form.register("name")}
                error={form.formState.errors.name?.message}
              />
              <FormField
                label="Description"
                registration={form.register("description")}
                error={form.formState.errors.description?.message}
              />
              <Form.Check
                id="department-active"
                label="Active department"
                {...form.register("active")}
              />
              <div className="form-actions">
                <Button type="submit" disabled={form.formState.isSubmitting}>
                  Save department
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
          <Form.Group controlId="department-search">
            <Form.Label>Search departments</Form.Label>
            <Form.Control
              value={q}
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
          <Table responsive hover className="mb-0">
            <thead>
              <tr>
                <th>Department</th>
                <th>Description</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {query.data.items.map((d) => (
                <tr key={d.id}>
                  <td>
                    <strong>{d.name}</strong>
                  </td>
                  <td>{d.description || "Not specified"}</td>
                  <td>{d.active ? "Active" : "Inactive"}</td>
                  <td>
                    <Button
                      size="sm"
                      variant="outline-secondary"
                      onClick={() => edit(d)}
                    >
                      Edit
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <Empty>No departments match your search.</Empty>
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
