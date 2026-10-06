import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { api, save } from "../api/client";
import { ClientsPage } from "../modules/clients/ClientsPage";
import { ResourcePanel } from "../modules/care/ResourcePanel";
import { admissionFields } from "../modules/care/fields";
import { rehabResources } from "../modules/rehabilitation/resources";
import { rx, adminFields } from "../modules/medication/MedicationPage";
import type { Resource } from "../modules/care/types";

const mocks = vi.hoisted(() => ({ can: vi.fn(() => true) }));
vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { id: "00000000-0000-4000-8000-000000000001" },
    can: mocks.can,
  }),
}));
vi.mock("../api/client", () => ({ api: vi.fn(), save: vi.fn() }));
const ids = {
  admission: "00000000-0000-4000-8000-000000000001",
  client: "00000000-0000-4000-8000-000000000002",
  med: "00000000-0000-4000-8000-000000000003",
  route: "00000000-0000-4000-8000-000000000004",
};
function mount(ui: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  vi.clearAllMocks();
  mocks.can.mockReturnValue(true);
  vi.mocked(api).mockResolvedValue({
    items: [],
    meta: { total: 0, page: 1, page_size: 20 },
  });
  vi.mocked(save).mockResolvedValue({ id: ids.client });
});
describe("Care workflow forms", () => {
  it("creates a permanent client from labelled identity fields", async () => {
    mount(<ClientsPage />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Create record" }));
    await user.type(screen.getByLabelText("First name *"), "Synthetic");
    await user.type(screen.getByLabelText("Surname *"), "Person");
    await user.clear(screen.getByLabelText("Date of birth *"));
    await user.type(screen.getByLabelText("Date of birth *"), "1990-03-05");
    await user.click(screen.getByRole("button", { name: "Save record" }));
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(
        "/clients",
        expect.objectContaining({
          first_name: "Synthetic",
          surname: "Person",
          date_of_birth: "1990-03-05",
          active: true,
        }),
      ),
    );
  });
  it("submits a screened referral admission with grouped intake fields", async () => {
    const resource: Resource = {
      title: "Admissions",
      path: "/admissions",
      permission: "admission.view",
      writePermission: "admission.create",
      fields: admissionFields,
      columns: [],
      defaults: {
        client_id: ids.client,
        referral_id: ids.med,
        reason: "Synthetic admission",
        programme: "Residential recovery",
      },
    };
    mount(<ResourcePanel resource={resource} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Create record" }));
    await user.click(screen.getByRole("button", { name: "Save record" }));
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(
        "/admissions",
        expect.objectContaining({
          client_id: ids.client,
          referral_id: ids.med,
          programme: "Residential recovery",
          expected_duration_days: 90,
        }),
      ),
    );
  });
  it("preserves admission context and measurable treatment objectives", async () => {
    const resource = {
      ...rehabResources[0],
      defaults: {
        presenting_problem: "Synthetic presentation",
        problem_area: "Recovery",
        goal: "Synthetic goal",
        responsible_professional_id: ids.client,
        start_date: "2026-10-05",
        target_date: "2026-11-05",
        review_date: "2026-10-12",
        objectives: [
          {
            description: "Attend sessions",
            measure: "Session attendance",
            intervention: "Structured counselling",
            target_date: "2026-11-05",
            completed: false,
          },
        ],
      },
    };
    mount(
      <ResourcePanel
        resource={resource}
        context={{ admission_id: ids.admission }}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Create record" }));
    await user.click(screen.getByRole("button", { name: "Save record" }));
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(
        "/rehabilitation/treatment-plans",
        expect.objectContaining({
          admission_id: ids.admission,
          objectives: [
            expect.objectContaining({
              measure: "Session attendance",
              target_date: "2026-11-05",
            }),
          ],
        }),
      ),
    );
  });
  it("records a counselling session with timezone-aware dates", async () => {
    const resource = {
      ...rehabResources[1],
      defaults: {
        session_type: "INDIVIDUAL_COUNSELLING",
        therapist_id: ids.client,
        start_at: "2026-10-05T10:00:00",
        end_at: "2026-10-05T11:00:00",
        objective: "Synthetic session",
        summary: "Synthetic summary",
        intervention: "Synthetic intervention",
        status: "COMPLETED",
      },
    };
    mount(
      <ResourcePanel
        resource={resource}
        context={{ admission_id: ids.admission }}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Create record" }));
    await user.click(screen.getByRole("button", { name: "Save record" }));
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(
        "/rehabilitation/sessions",
        expect.objectContaining({
          admission_id: ids.admission,
          start_at: "2026-10-05T07:00:00.000Z",
          end_at: "2026-10-05T08:00:00.000Z",
          summary: "Synthetic summary",
        }),
      ),
    );
  });
  it("submits medication, unit and route with a schedule", async () => {
    const resource = {
      ...rx,
      defaults: {
        medication_id: ids.med,
        dose: "1",
        dose_unit: "tablet",
        route_id: ids.route,
        frequency: "Once daily",
        indication: "Synthetic indication",
      },
    };
    mount(
      <ResourcePanel
        resource={resource}
        context={{ admission_id: ids.admission }}
      />,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Create record" }));
    await user.click(screen.getByRole("button", { name: "Save record" }));
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(
        "/medication/prescriptions",
        expect.objectContaining({
          admission_id: ids.admission,
          medication_id: ids.med,
          route_id: ids.route,
          dose: 1,
          scheduled_times: ["08:00"],
        }),
      ),
    );
  });
  it("records an eMAR outcome against the selected scheduled dose", async () => {
    const row = {
      id: ids.med,
      prescription_id: ids.route,
      prescribed_dose: "1",
      status: "DUE",
    };
    vi.mocked(api).mockResolvedValue({
      items: [row],
      meta: { total: 1, page: 1, page_size: 20 },
    });
    const resource: Resource = {
      title: "Medication due",
      path: "/medication/due",
      permission: "medication.view",
      columns: [{ key: "status", label: "Status" }],
      actions: [
        {
          label: "Record administration outcome",
          permission: "medication.administer",
          path: () => "/medication/administrations",
          fields: adminFields,
          defaults: (r) => ({
            prescription_id: r.prescription_id,
            dose_id: r.id,
            actual_dose: r.prescribed_dose,
            status: "GIVEN",
          }),
        },
      ],
    };
    mount(<ResourcePanel resource={resource} />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Open" }));
    await user.click(
      screen.getByRole("button", { name: "Record administration outcome" }),
    );
    // Action button and submit button share a label; submit the form explicitly.
    const buttons = screen.getAllByRole("button", {
      name: "Record administration outcome",
    });
    await user.click(buttons.at(-1)!);
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith(
        "/medication/administrations",
        expect.objectContaining({
          dose_id: ids.med,
          prescription_id: ids.route,
          actual_dose: 1,
          status: "GIVEN",
        }),
        "POST",
      ),
    );
  });
  it("keeps care creation unavailable until an admission is selected", () => {
    mount(<ResourcePanel resource={rehabResources[0]} />);
    expect(
      screen.getByRole("button", { name: "Create record" }),
    ).toBeDisabled();
  });
  it("hides denied resources without issuing record requests", () => {
    mocks.can.mockReturnValue(false);
    mount(<ResourcePanel resource={rx} />);
    expect(screen.getByText(/does not have access/)).toBeInTheDocument();
    expect(api).not.toHaveBeenCalled();
  });
});
