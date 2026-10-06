import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { useQuery } from "@tanstack/react-query";
import { Accordion, Button, Form } from "react-bootstrap";
import { api } from "../../api/client";
import { ErrorNotice } from "../../components/Common";
import { buildSchema, initialValues } from "./validation";
import type { Choice, Field, Values } from "./types";

function Lookup({
  field,
  value,
  onChange,
  id,
}: {
  field: Field;
  value: unknown;
  onChange: (v: unknown) => void;
  id: string;
}) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const path = field.source ?? "";
  const query = useQuery({
    queryKey: ["lookup", path, search, page],
    queryFn: () =>
      api<Values>(
        `${path}${path.includes("?") ? "&" : "?"}page_size=20&page=${page}&q=${encodeURIComponent(search)}`,
      ),
    enabled: !!path,
  });
  const records =
    (query.data?.[field.sourceKey ?? "items"] as Values[] | undefined) ?? [];
  const choices: Choice[] = records.map((row) => ({
    value: String(row.id),
    label: (
      field.labelKeys ?? [
        "name",
        "generic_name",
        "full_name",
        "client_number",
        "first_name",
        "surname",
        "admission_number",
        "batch_number",
      ]
    )
      .map((k) => row[k])
      .filter((v) => v !== null && v !== undefined && v !== "")
      .join(" · "),
  }));
  const meta = query.data?.meta as { total: number } | undefined;
  return (
    <>
      <Form.Control
        aria-label={`Search ${field.label}`}
        placeholder={`Search ${field.label.toLowerCase()}`}
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(1);
        }}
        className="mb-1"
      />
      <Form.Select
        id={id}
        value={typeof value === "string" ? value : ""}
        onChange={(e) => onChange(e.target.value)}
        aria-required={field.required}
      >
        <option value="">Choose {field.label.toLowerCase()}</option>
        {value && !choices.some((c) => c.value === value) ? (
          <option value={String(value)}>
            Current selection ({String(value).slice(0, 8)})
          </option>
        ) : null}
        {choices.map((c) => (
          <option key={c.value} value={c.value}>
            {c.label}
          </option>
        ))}
      </Form.Select>
      {query.isPending && <small>Loading choices…</small>}
      <ErrorNotice error={query.error} />
      {meta && meta.total > 20 && (
        <div className="d-flex gap-2 mt-1">
          <Button
            size="sm"
            variant="outline-secondary"
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
          >
            Previous choices
          </Button>
          <Button
            size="sm"
            variant="outline-secondary"
            disabled={page * 20 >= meta.total}
            onClick={() => setPage(page + 1)}
          >
            Next choices
          </Button>
        </div>
      )}
    </>
  );
}
function Editor({
  field,
  value,
  onChange,
  id,
}: {
  field: Field;
  value: unknown;
  onChange: (v: unknown) => void;
  id: string;
}) {
  if (field.type === "lookup")
    return <Lookup field={field} value={value} onChange={onChange} id={id} />;
  if (field.type === "checkbox")
    return (
      <Form.Check
        id={id}
        label={field.label}
        checked={!!value}
        onChange={(e) => onChange(e.target.checked)}
      />
    );
  if (field.type === "select")
    return (
      <Form.Select
        id={id}
        value={typeof value === "string" ? value : ""}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Choose an option</option>
        {field.options?.map((option) =>
          typeof option === "string" ? (
            <option key={option} value={option}>
              {option.replaceAll("_", " ")}
            </option>
          ) : (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ),
        )}
      </Form.Select>
    );
  if (field.type === "array") {
    const rows = Array.isArray(value) ? (value as Values[]) : [];
    return (
      <div id={id}>
        {rows.map((row, index) => (
          <fieldset key={index} className="nested-fields mb-3">
            <legend className="fs-6">
              {field.label} {index + 1}
            </legend>
            <div className="row g-3">
              {field.fields?.map((child) => (
                <div
                  className={
                    child.type === "array" || child.type === "textarea"
                      ? "col-12"
                      : "col-md-6"
                  }
                  key={child.name}
                >
                  <Form.Label htmlFor={`${id}-${index}-${child.name}`}>
                    {child.type === "checkbox" ? "" : child.label}
                  </Form.Label>
                  <Editor
                    field={child}
                    id={`${id}-${index}-${child.name}`}
                    value={row[child.name]}
                    onChange={(v) =>
                      onChange(
                        rows.map((r, i) =>
                          i === index ? { ...r, [child.name]: v } : r,
                        ),
                      )
                    }
                  />
                </div>
              ))}
            </div>
            <Button
              size="sm"
              variant="outline-danger"
              className="mt-3"
              onClick={() => onChange(rows.filter((_, i) => i !== index))}
            >
              Remove {field.label.toLowerCase()}
            </Button>
          </fieldset>
        ))}
        <Button
          size="sm"
          variant="outline-secondary"
          onClick={() => onChange([...rows, initialValues(field.fields ?? [])])}
        >
          Add {field.label.toLowerCase()}
        </Button>
      </div>
    );
  }
  if (field.type === "object") {
    const record = (value ?? {}) as Values;
    return (
      <div className="row g-3" id={id}>
        {field.fields?.map((child) => (
          <div className="col-md-6" key={child.name}>
            <Form.Label htmlFor={`${id}-${child.name}`}>
              {child.label}
            </Form.Label>
            <Editor
              field={child}
              value={record[child.name]}
              onChange={(v) => onChange({ ...record, [child.name]: v })}
              id={`${id}-${child.name}`}
            />
          </div>
        ))}
      </div>
    );
  }
  if (field.type === "file")
    return (
      <Form.Control
        id={id}
        type="file"
        accept={field.accept ?? "application/pdf"}
        onChange={async (e) => {
          const file = (e.target as HTMLInputElement).files?.[0];
          if (!file) return;
          if (file.size > 5 * 1024 * 1024) {
            onChange("");
            return;
          }
          const bytes = new Uint8Array(await file.arrayBuffer());
          let binary = "";
          for (const byte of bytes) binary += String.fromCharCode(byte);
          onChange(btoa(binary));
        }}
      />
    );
  const rendered =
    field.type === "strings" && Array.isArray(value)
      ? value.join("\n")
      : typeof value === "string" || typeof value === "number"
        ? value
        : "";
  if (field.type === "textarea" || field.type === "strings")
    return (
      <Form.Control
        id={id}
        as="textarea"
        rows={3}
        value={rendered}
        onChange={(e) => onChange(e.target.value)}
        aria-required={field.required}
      />
    );
  return (
    <Form.Control
      id={id}
      type={
        field.type === "datetime-local"
          ? "datetime-local"
          : field.type === "date"
            ? "date"
            : field.type === "number"
              ? "number"
              : "text"
      }
      step={
        field.type === "number"
          ? "any"
          : field.type === "datetime-local"
            ? "1"
            : undefined
      }
      min={field.min}
      max={field.type === "number" ? field.max : undefined}
      value={rendered}
      onChange={(e) => onChange(e.target.value)}
      aria-required={field.required}
    />
  );
}
export function RecordForm({
  fields,
  defaults = {},
  onSubmit,
  onCancel,
  submitLabel = "Save record",
}: {
  fields: Field[];
  defaults?: Values;
  onSubmit: (data: Values) => Promise<void>;
  onCancel?: () => void;
  submitLabel?: string;
}) {
  const [error, setError] = useState("");
  const form = useForm<Values>({
    defaultValues: initialValues(fields, defaults),
  });
  const sections = [
    ...new Set(fields.map((f) => f.section ?? "Record details")),
  ];
  return (
    <Form
      noValidate
      onSubmit={form.handleSubmit(async (values) => {
        setError("");
        form.clearErrors();
        const parsed = buildSchema(fields).safeParse(values);
        if (!parsed.success) {
          for (const issue of parsed.error.issues)
            form.setError(String(issue.path[0]), { message: issue.message });
          setError(
            parsed.error.issues
              .map((i) => `${i.path.join(".")}: ${i.message}`)
              .join("; "),
          );
          return;
        }
        try {
          await onSubmit(parsed.data);
        } catch (e) {
          setError(e instanceof Error ? e.message : String(e));
        }
      })}
    >
      <ErrorNotice error={error} />
      <Accordion defaultActiveKey="0" alwaysOpen>
        {sections.map((section, index) => (
          <Accordion.Item eventKey={String(index)} key={section}>
            <Accordion.Header>{section}</Accordion.Header>
            <Accordion.Body>
              <div className="row g-3">
                {fields
                  .filter((f) => (f.section ?? "Record details") === section)
                  .map((field) => (
                    <Form.Group
                      className={
                        field.type === "textarea" ||
                        field.type === "strings" ||
                        field.type === "array" ||
                        field.type === "object"
                          ? "col-12"
                          : "col-md-6"
                      }
                      key={field.name}
                    >
                      <Form.Label htmlFor={`field-${field.name}`}>
                        {field.type === "checkbox" ? "" : field.label}
                        {field.required && field.type !== "checkbox"
                          ? " *"
                          : ""}
                      </Form.Label>
                      <Controller
                        name={field.name}
                        control={form.control}
                        render={({ field: binding }) => (
                          <Editor
                            field={field}
                            id={`field-${field.name}`}
                            value={binding.value}
                            onChange={binding.onChange}
                          />
                        )}
                      />
                      {field.help && <Form.Text>{field.help}</Form.Text>}
                      {form.formState.errors[field.name] && (
                        <div className="text-danger small">
                          {String(form.formState.errors[field.name]?.message)}
                        </div>
                      )}
                    </Form.Group>
                  ))}
              </div>
            </Accordion.Body>
          </Accordion.Item>
        ))}
      </Accordion>
      <div className="form-actions">
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {form.formState.isSubmitting ? "Saving…" : submitLabel}
        </Button>
        {onCancel && (
          <Button variant="outline-secondary" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>
    </Form>
  );
}
