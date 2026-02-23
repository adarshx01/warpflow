const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface RequestOptions {
  method?: string;
  body?: unknown;
  skipAuthRedirect?: boolean;
}

function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export async function api<T = unknown>(
  path: string,
  { method = "GET", body, skipAuthRedirect = false }: RequestOptions = {}
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const csrf = getCsrfToken();
  if (csrf && method !== "GET") {
    headers["X-CSRF-Token"] = csrf;
  }

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    credentials: "include", // send & receive httpOnly cookies
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    if (!skipAuthRedirect) {
      window.location.href = '/login';
    }
    throw new Error('Session expired. Please log in again.');
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}
