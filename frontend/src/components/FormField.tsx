import { Form } from "react-bootstrap";
import type { UseFormRegisterReturn } from "react-hook-form";

export function FormField({
  label,
  registration,
  error,
  type = "text",
  required = false,
  autoComplete,
  help,
}: {
  label: string;
  registration: UseFormRegisterReturn;
  error?: string;
  type?: string;
  required?: boolean;
  autoComplete?: string;
  help?: string;
}) {
  return (
    <Form.Group className="mb-3" controlId={registration.name}>
      <Form.Label>
        {label}
        {required && <span aria-hidden="true"> *</span>}
      </Form.Label>
      <Form.Control
        type={type}
        {...registration}
        isInvalid={!!error}
        aria-invalid={!!error || undefined}
        autoComplete={autoComplete}
        aria-required={required}
        aria-describedby={
          [
            help && `${registration.name}-help`,
            error && `${registration.name}-error`,
          ]
            .filter(Boolean)
            .join(" ") || undefined
        }
      />
      <Form.Control.Feedback type="invalid" id={`${registration.name}-error`}>
        {error}
      </Form.Control.Feedback>
      {help && <Form.Text id={`${registration.name}-help`}>{help}</Form.Text>}
    </Form.Group>
  );
}
