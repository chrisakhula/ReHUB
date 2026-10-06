import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Alert, Button, Form } from "react-bootstrap";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { save } from "../../api/client";
import { identityApi } from "../../api/identity";
import { facilitySchema } from "../../schemas/administration";
import type { Facility } from "../../types/identity";
import { ErrorNotice, Loading, PageHeader } from "../../components/Common";
import { FormField } from "../../components/FormField";

function SettingsForm({ facility }: { facility: Facility }) {
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const cache = useQueryClient();
  const form = useForm<z.infer<typeof facilitySchema>>({
    resolver: zodResolver(facilitySchema),
    defaultValues: {
      ...facility,
      contact_email: facility.contact_email ?? "",
      phone: facility.phone ?? "",
      address: facility.address ?? "",
      logo_url: facility.logo_url ?? "",
    },
  });
  return (
    <Form
      noValidate
      onSubmit={form.handleSubmit(async (data) => {
        try {
          await save(
            "/settings",
            {
              ...data,
              contact_email: data.contact_email || null,
              phone: data.phone || null,
              address: data.address || null,
              logo_url: data.logo_url || null,
            },
            "PUT",
          );
          setSaved(true);
          setError("");
          await cache.invalidateQueries({ queryKey: ["settings"] });
        } catch (e) {
          setError(String(e));
        }
      })}
    >
      <ErrorNotice error={error} />
      {saved && <Alert variant="success">Institution settings saved.</Alert>}
      <div className="row g-4">
        <div className="col-lg-6">
          <section className="card">
            <div className="card-header">
              <h2>Institution identity</h2>
            </div>
            <div className="card-body">
              <FormField
                label="Institution name"
                required
                registration={form.register("name")}
                error={form.formState.errors.name?.message}
              />
              <FormField
                label="System name"
                required
                registration={form.register("system_name")}
                error={form.formState.errors.system_name?.message}
              />
              <FormField
                label="Short name"
                required
                registration={form.register("short_name")}
                error={form.formState.errors.short_name?.message}
              />
              <FormField
                label="Institution logo URL"
                registration={form.register("logo_url")}
                error={form.formState.errors.logo_url?.message}
              />
              <p className="small text-secondary">
                Use an HTTPS image hosted by your institution. Do not include
                sensitive information in the image URL.
              </p>
            </div>
          </section>
        </div>
        <div className="col-lg-6">
          <section className="card">
            <div className="card-header">
              <h2>Contact details</h2>
            </div>
            <div className="card-body">
              <FormField
                label="Contact email"
                type="email"
                registration={form.register("contact_email")}
                error={form.formState.errors.contact_email?.message}
              />
              <FormField
                label="Phone number"
                registration={form.register("phone")}
                error={form.formState.errors.phone?.message}
              />
              <Form.Group controlId="address">
                <Form.Label>Physical address</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={4}
                  {...form.register("address")}
                  isInvalid={!!form.formState.errors.address}
                />
                <Form.Control.Feedback type="invalid">
                  {form.formState.errors.address?.message}
                </Form.Control.Feedback>
              </Form.Group>
            </div>
          </section>
        </div>
      </div>
      <div className="form-actions">
        <Button type="submit" disabled={form.formState.isSubmitting}>
          Save settings
        </Button>
      </div>
    </Form>
  );
}
export function SettingsPage() {
  const query = useQuery({
    queryKey: ["settings"],
    queryFn: identityApi.settings,
  });
  return (
    <>
      <PageHeader
        title="Institution settings"
        description="Configure system identity and institutional contact information."
      />
      <ErrorNotice error={query.error} />
      {query.isPending ? (
        <Loading />
      ) : (
        query.data && <SettingsForm facility={query.data} />
      )}
    </>
  );
}
