export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
function csrfToken() {
  return (
    document.cookie
      .split("; ")
      .find((value) => value.startsWith("csrf_token="))
      ?.split("=")[1] ?? ""
  );
}
let refreshPromise: Promise<Response> | null = null;
export async function api<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = {
    "Content-Type": "application/json",
    "X-CSRF-Token": csrfToken(),
    ...options.headers,
  };
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers,
    credentials: "include",
  });
  if (
    response.status === 401 &&
    retry &&
    ![
      "/auth/login",
      "/auth/refresh",
      "/auth/request-reset",
      "/auth/reset-password",
    ].includes(path)
  ) {
    refreshPromise ??= fetch("/api/v1/auth/refresh", {
      method: "POST",
      credentials: "include",
      headers: { "X-CSRF-Token": csrfToken() },
    }).finally(() => {
      refreshPromise = null;
    });
    const refresh = await refreshPromise;
    if (refresh.ok) return api<T>(path, options, false);
    window.dispatchEvent(new Event("session-expired"));
  }
  const data: unknown = await response.json();
  if (!response.ok) {
    const error = data as {
      error?: {
        message?: string;
        fields?: { field: string; message: string }[];
      };
    };
    const fields = error.error?.fields
      ?.map((f) => `${f.field}: ${f.message}`)
      .join("; ");
    throw new ApiError(
      response.status,
      fields ?? error.error?.message ?? "Request failed",
    );
  }
  return data as T;
}
export function save<T>(path: string, data: unknown, method = "POST") {
  return api<T>(path, { method, body: JSON.stringify(data) });
}
