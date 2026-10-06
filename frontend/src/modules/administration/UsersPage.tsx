import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Form, Table } from "react-bootstrap";
import { api } from "../../api/client";
import type { Page, User } from "../../types/identity";
import {
  Empty,
  ErrorNotice,
  Loading,
  PageHeader,
  Pagination,
} from "../../components/Common";

export function UsersPage() {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [active, setActive] = useState("");
  const [sort, setSort] = useState("full_name");
  const query = useQuery({
    queryKey: ["users", page, q, active, sort],
    queryFn: () =>
      api<Page<User>>(
        `/users?page=${page}&q=${encodeURIComponent(q)}&sort=${sort}${active ? `&active=${active}` : ""}`,
      ),
  });
  return (
    <>
      <PageHeader
        title="User management"
        description="Manage staff accounts and institutional access."
        action={
          <Link className="btn btn-primary" to="/administration/users/new">
            <i className="bi bi-plus-lg me-2" />
            Create user
          </Link>
        }
      />
      <section className="card">
        <div className="table-toolbar">
          <Form.Group controlId="user-search">
            <Form.Label>Search staff</Form.Label>
            <Form.Control
              placeholder="Name or email address"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setPage(1);
              }}
            />
          </Form.Group>
          <Form.Group controlId="account-filter">
            <Form.Label>Account status</Form.Label>
            <Form.Select
              value={active}
              onChange={(e) => {
                setActive(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All accounts</option>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </Form.Select>
          </Form.Group>
          <Form.Group controlId="user-sort">
            <Form.Label>Sort by</Form.Label>
            <Form.Select
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                setPage(1);
              }}
            >
              <option value="full_name">Name</option>
              <option value="email">Email</option>
              <option value="created_at">Created date</option>
            </Form.Select>
          </Form.Group>
        </div>
        <ErrorNotice error={query.error} />
        {query.isPending ? (
          <Loading />
        ) : query.data?.items.length ? (
          <div className="table-responsive">
            <Table hover className="mb-0">
              <thead>
                <tr>
                  <th>Staff member</th>
                  <th>Assigned roles</th>
                  <th>Status</th>
                  <th>Last sign in</th>
                  <th>
                    <span className="visually-hidden">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {query.data.items.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <strong>{user.full_name}</strong>
                      <small className="d-block text-secondary">
                        {user.email}
                      </small>
                    </td>
                    <td>
                      {user.roles.map((r) => r.name).join(", ") ||
                        "No role assigned"}
                    </td>
                    <td>
                      <span
                        className={`status-badge ${user.active ? "active-status" : "inactive-status"}`}
                      >
                        {user.active ? "Active" : "Inactive"}
                      </span>
                      {user.force_password_change && (
                        <small className="d-block text-secondary mt-1">
                          Password change required
                        </small>
                      )}
                    </td>
                    <td>
                      {user.last_login
                        ? new Date(user.last_login).toLocaleDateString("en-KE")
                        : "Never"}
                    </td>
                    <td>
                      <Link
                        to="/administration/users/new"
                        state={{ user }}
                        className="btn btn-sm btn-outline-secondary"
                        aria-label={`Edit ${user.full_name}`}
                      >
                        Edit
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
        ) : (
          !query.error && <Empty>No staff accounts match these filters.</Empty>
        )}
        <Pagination
          page={page}
          total={query.data?.meta.total ?? 0}
          onChange={setPage}
        />
      </section>
      <p className="small text-secondary mt-3">
        <i className="bi bi-shield-lock me-1" />
        Changes to access are recorded. Updating an account revokes its existing
        sessions.
      </p>
    </>
  );
}
