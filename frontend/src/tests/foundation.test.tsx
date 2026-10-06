import { vi, describe, it, expect, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LoginPage } from "../modules/auth/LoginPage";
import { ChangePasswordPage } from "../modules/auth/PasswordPages";
import { UserFormPage } from "../modules/administration/UserFormPage";
import { RolesPage } from "../modules/administration/RolesPage";
import { AppRoutes } from "../routes/AppRoutes";
import { ApiError, api, save } from "../api/client";

const mocks = vi.hoisted(() => ({
  login: vi.fn(),
  logout: vi.fn(),
  clear: vi.fn(),
  can: vi.fn(() => true),
  user: null as unknown,
  roles: vi.fn(),
  permissions: vi.fn(),
  departments: vi.fn(),
}));
vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: mocks.user,
    loading: false,
    error: "",
    login: mocks.login,
    logout: mocks.logout,
    can: mocks.can,
    clear: mocks.clear,
  }),
}));
vi.mock("../api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/client")>()),
  api: vi.fn(),
  save: vi.fn(),
}));
vi.mock("../api/identity", () => ({
  identityApi: {
    roles: mocks.roles,
    permissions: mocks.permissions,
    departments: mocks.departments,
  },
}));
function wrapper(ui: React.ReactNode, path = "/") {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.clearAllMocks();
  mocks.user = null;
  mocks.can.mockReturnValue(true);
  mocks.logout.mockResolvedValue(undefined);
  mocks.roles.mockResolvedValue({
    items: [{ id: "r1", name: "Auditor", description: "", permissions: [] }],
    meta: { total: 1 },
  });
  mocks.permissions.mockResolvedValue({ items: [], meta: { total: 0 } });
  mocks.departments.mockResolvedValue({ items: [], meta: { total: 0 } });
  vi.mocked(save).mockResolvedValue({});
  vi.mocked(api).mockResolvedValue({ items: [], meta: { total: 0 } });
});
describe("Phase 1 workflows", () => {
  it("validates login and signs in with entered credentials", async () => {
    wrapper(<LoginPage />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(
      await screen.findByText("Enter a valid email address"),
    ).toBeInTheDocument();
    expect(mocks.login).not.toHaveBeenCalled();
    await user.type(
      screen.getByLabelText(/Email address/),
      "staff@example.org",
    );
    await user.type(screen.getByLabelText(/Password/), "StrongPassword!2026");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() =>
      expect(mocks.login).toHaveBeenCalledWith(
        "staff@example.org",
        "StrongPassword!2026",
      ),
    );
  });
  it("shows a failed login error", async () => {
    mocks.login.mockRejectedValueOnce(new Error("Invalid credentials"));
    wrapper(<LoginPage />);
    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText(/Email address/),
      "staff@example.org",
    );
    await user.type(screen.getByLabelText(/Password/), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid credentials",
    );
  });
  it("creates a staff account with selected role and validated password", async () => {
    wrapper(<UserFormPage />);
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText(/Full name/), "Sample Staff");
    await user.type(
      screen.getByLabelText(/Email address/),
      "sample@example.org",
    );
    await user.type(screen.getByLabelText(/Temporary password/), "short");
    await user.click(screen.getByLabelText("Auditor"));
    await user.click(screen.getByRole("button", { name: "Create user" }));
    expect(
      await screen.findByText("Use at least 12 characters"),
    ).toBeInTheDocument();
    expect(save).not.toHaveBeenCalled();
    await user.clear(screen.getByLabelText(/Temporary password/));
    await user.type(
      screen.getByLabelText(/Temporary password/),
      "Temporary!2026",
    );
    await user.click(screen.getByRole("button", { name: "Create user" }));
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(
        "/users",
        expect.objectContaining({
          full_name: "Sample Staff",
          role_ids: ["r1"],
          department_id: null,
        }),
        "POST",
      ),
    );
  });
  it("requires a reason and saves a role", async () => {
    wrapper(<RolesPage />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Create role" }));
    await user.type(screen.getByLabelText(/Role name/), "Audit reviewer");
    await user.click(screen.getByRole("button", { name: "Save role" }));
    expect(save).not.toHaveBeenCalled();
    await user.type(
      screen.getByLabelText(/Reason for change/),
      "Quality review",
    );
    await user.click(screen.getByRole("button", { name: "Save role" }));
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(
        "/roles",
        expect.objectContaining({
          name: "Audit reviewer",
          reason: "Quality review",
        }),
        "POST",
      ),
    );
  });
  it("guards unauthenticated routes", async () => {
    wrapper(<AppRoutes />, "/administration/users");
    expect(
      await screen.findByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
  });
  it("requires first-login password change", async () => {
    mocks.user = { force_password_change: true };
    wrapper(<AppRoutes />, "/administration/users");
    expect(
      await screen.findByRole("heading", { name: "Change your password" }),
    ).toBeInTheDocument();
  });
  it("identifies the account and submits distinct current and new passwords", async () => {
    mocks.user = { email: "staff@example.org", force_password_change: true };
    wrapper(<ChangePasswordPage />);
    const user = userEvent.setup();
    expect(screen.getByText("staff@example.org")).toBeInTheDocument();
    expect(
      screen.getByText(
        /Enter the temporary password you used to sign in, then/,
      ),
    ).toBeInTheDocument();
    const current = screen.getByLabelText("Current password", { exact: true });
    await user.type(current, "ReplacementTemporary!2026");
    await user.type(
      screen.getByLabelText("New password", { exact: true }),
      "PersonalPassword!2026",
    );
    expect(current).toHaveAttribute("type", "password");
    await user.click(
      screen.getByRole("checkbox", { name: "Show current password" }),
    );
    expect(current).toHaveAttribute("type", "text");
    expect(current).toHaveValue("ReplacementTemporary!2026");
    await user.click(
      screen.getByRole("checkbox", { name: "Show current password" }),
    );
    expect(current).toHaveAttribute("type", "password");
    await user.click(screen.getByRole("button", { name: "Update password" }));
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith("/auth/change-password", {
        current_password: "ReplacementTemporary!2026",
        new_password: "PersonalPassword!2026",
      }),
    );
    expect(mocks.clear).toHaveBeenCalledOnce();
  });
  it("focuses an incorrect current password and preserves the new password for retry", async () => {
    mocks.user = { email: "staff@example.org", force_password_change: true };
    vi.mocked(save).mockRejectedValueOnce(
      new ApiError(400, "Current password is incorrect"),
    );
    wrapper(<ChangePasswordPage />);
    const user = userEvent.setup();
    const current = screen.getByLabelText("Current password", { exact: true });
    const next = screen.getByLabelText("New password", { exact: true });
    await user.type(current, "OldPassword!2026");
    await user.type(next, "PersonalPassword!2026");
    await user.click(screen.getByRole("button", { name: "Update password" }));
    expect(
      await screen.findByText(
        /Replace any old password filled in by your browser/,
      ),
    ).toBeInTheDocument();
    expect(current).toHaveFocus();
    expect(current).toHaveAttribute("aria-invalid", "true");
    expect(current).toHaveAttribute(
      "aria-describedby",
      "current_password-help current_password-error",
    );
    expect(next).toHaveValue("PersonalPassword!2026");
    expect(mocks.clear).not.toHaveBeenCalled();
    await user.clear(current);
    await user.type(current, "ReplacementTemporary!2026");
    await user.click(screen.getByRole("button", { name: "Update password" }));
    await waitFor(() => expect(mocks.clear).toHaveBeenCalledOnce());
    expect(save).toHaveBeenLastCalledWith("/auth/change-password", {
      current_password: "ReplacementTemporary!2026",
      new_password: "PersonalPassword!2026",
    });
  });
  it("allows signing out of the forced password-change page", async () => {
    mocks.user = { email: "staff@example.org", force_password_change: true };
    wrapper(<ChangePasswordPage />);
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Sign out" }));
    await waitFor(() => expect(mocks.logout).toHaveBeenCalledOnce());
    expect(save).not.toHaveBeenCalled();
  });
});
