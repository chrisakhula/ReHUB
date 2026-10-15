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
  if (response.status === 204) {
    if (!response.ok) {
      throw new ApiError(response.status, response.statusText || "Request failed");
    }
    return {} as T;
  }
  const text = await response.text();
  let data: unknown = null;
  if (text && text.trim().length > 0) {
    try {
      data = JSON.parse(text);
    } catch {
      if (!response.ok) {
        const isHtml = text.toLowerCase().includes("<html");
        const fallbackMsg = isHtml
          ? response.statusText || "Request failed"
          : text.slice(0, 200).trim();
        throw new ApiError(response.status, fallbackMsg || "Request failed");
      }
      throw new ApiError(response.status, "Invalid response received from server");
    }
  }
  if (!response.ok) {
    const error =
      data && typeof data === "object"
        ? (data as {
            error?: {
              message?: string;
              fields?: { field: string; message: string }[];
            };
            detail?: string | { msg?: string }[];
          })
        : null;
    const fields = error?.error?.fields
      ?.map((f) => `${f.field}: ${f.message}`)
      .join("; ");
    const detailMsg = Array.isArray(error?.detail)
      ? error?.detail
          .map((d) => (typeof d === "string" ? d : d.msg || JSON.stringify(d)))
          .join("; ")
      : typeof error?.detail === "string"
        ? error.detail
        : undefined;

    throw new ApiError(
      response.status,
      fields ?? error?.error?.message ?? detailMsg ?? response.statusText ?? "Request failed",
    );
  }
  return data as T;
}
export function save<T>(path: string, data: unknown, method = "POST") {
  return api<T>(path, { method, body: JSON.stringify(data) });
}
