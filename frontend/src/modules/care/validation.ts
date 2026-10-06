import { z } from "zod";
import type { Field, Values } from "./types";

export const nowEAT = () =>
  new Date(Date.now() + 3 * 60 * 60 * 1000).toISOString().slice(0, 19);
export const todayEAT = () => nowEAT().slice(0, 10);
export function inputDate(value: unknown): string {
  return typeof value === "string" && value
    ? new Date(new Date(value).getTime() + 3 * 3600000)
        .toISOString()
        .slice(0, 19)
    : "";
}
function fieldSchema(field: Field): z.ZodType {
  let schema: z.ZodType;
  if (field.type === "number") {
    let numeric = z.number();
    if (field.min !== undefined) numeric = numeric.min(field.min);
    if (field.max !== undefined) numeric = numeric.max(field.max);
    schema = z.preprocess(
      (v) =>
        v === "" || v === null || v === undefined ? undefined : Number(v),
      numeric,
    );
  } else if (field.type === "checkbox") schema = z.boolean();
  else if (field.type === "array")
    schema = field.required
      ? z
          .array(buildSchema(field.fields ?? []))
          .min(1, `Add at least one ${field.label.toLowerCase()}`)
      : z.array(buildSchema(field.fields ?? []));
  else if (field.type === "object") schema = buildSchema(field.fields ?? []);
  else if (field.type === "strings")
    schema = z.preprocess(
      (v) =>
        typeof v === "string"
          ? v
              .split(/[\n,]/)
              .map((s) => s.trim())
              .filter(Boolean)
          : v,
      z.array(z.string().max(6000)),
    );
  else {
    let string = z
      .string()
      .trim()
      .max(field.max ?? 10000);
    if (field.required) string = string.min(1, `${field.label} is required`);
    schema =
      field.type === "select"
        ? string.refine(
            (v) =>
              (field.options ?? []).some(
                (option) =>
                  (typeof option === "string" ? option : option.value) === v,
              ),
            "Choose a valid option",
          )
        : string;
    if (field.type === "datetime-local")
      schema = string
        .refine(
          (v) => !v || !Number.isNaN(Date.parse(v)),
          "Enter a valid date and time",
        )
        .transform((v) =>
          v
            ? new Date(
                `${v}${v.length === 16 ? ":00" : ""}+03:00`,
              ).toISOString()
            : undefined,
        );
  }
  if (
    !field.required &&
    field.type !== "checkbox" &&
    field.type !== "array" &&
    field.type !== "object" &&
    field.type !== "strings"
  ) {
    schema = z.preprocess(
      (v) => (v === "" || v === null ? undefined : v),
      schema.optional(),
    );
  }
  return schema;
}
export function buildSchema(fields: Field[]) {
  return z.object(
    Object.fromEntries(fields.map((field) => [field.name, fieldSchema(field)])),
  );
}
export function initialValues(fields: Field[], defaults: Values = {}): Values {
  return Object.fromEntries(
    fields.map((field) => {
      let value = defaults[field.name] ?? field.default;
      if (typeof value === "function") value = (value as () => unknown)();
      if (
        field.type === "select" &&
        !(field.options ?? []).some(
          (option) =>
            (typeof option === "string" ? option : option.value) === value,
        )
      )
        value = field.default;
      if (value === undefined)
        value =
          field.type === "checkbox"
            ? false
            : field.type === "array" || field.type === "strings"
              ? []
              : field.type === "object"
                ? initialValues(field.fields ?? [])
                : "";
      if (
        field.type === "datetime-local" &&
        typeof value === "string" &&
        /T.*(?:Z|[+-]\d\d:\d\d)$/.test(value)
      )
        value = inputDate(value);
      if (field.type === "number" && value !== "" && value !== null)
        value = Number(value);
      return [field.name, value];
    }),
  );
}
