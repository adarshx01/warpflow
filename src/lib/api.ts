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

// Error details that come from the Google Docs integration and are NOT session
// expiry — they should be shown as inline errors in the UI, not cause a logout.
const GOOGLE_CREDENTIAL_ERRORS = [
  "google account not connected",
  "please complete oauth flow",
];

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
    // Read the error body before deciding what to do.
    const errorBody = await res.json().catch(() => ({ detail: "" }));
    const detail: string = (errorBody.detail ?? "").toLowerCase();

    // If it's a Google credential "not connected" error, surface it as a
    // regular thrown error so the UI can show it inline. Do NOT log the user out.
    const isGoogleCredentialError = GOOGLE_CREDENTIAL_ERRORS.some((msg) =>
      detail.includes(msg)
    );

    if (!isGoogleCredentialError && !skipAuthRedirect) {
      window.location.href = '/login';
    }

    throw new Error(
      isGoogleCredentialError
        ? "Google account not connected. Click 'Re-connect Google' and complete the OAuth flow first."
        : "Session expired. Please log in again."
    );
  }

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

