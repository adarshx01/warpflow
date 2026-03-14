import { api } from './api';

export type SecretKey =
  | 'google_oauth_client_id'
  | 'google_oauth_client_secret'
  | 'agent_openai_api_key'
  | 'agent_gemini_api_key';

interface SecretResponse {
  exists: boolean;
  // value is null for agent API keys — the backend never sends them to the frontend
  value: string | null;
}

/** Returns the stored value for non-agent secrets (e.g. Google OAuth client id/secret),
 *  or null if the secret doesn't exist or is a backend-only agent key. */
export async function getSecret(secretKey: SecretKey): Promise<string | null> {
  try {
    const data = await api<SecretResponse>(`/api/secrets/${secretKey}`);
    return data.value ?? null;
  } catch {
    return null;
  }
}

/** Returns true if the secret exists in the backend store, false otherwise.
 *  Safe to call for all key types including backend-only agent API keys. */
export async function checkSecretExists(secretKey: SecretKey): Promise<boolean> {
  try {
    const data = await api<SecretResponse>(`/api/secrets/${secretKey}`);
    return data.exists;
  } catch {
    return false;
  }
}

export async function setSecret(secretKey: SecretKey, value: string): Promise<void> {
  await api(`/api/secrets/${secretKey}`, {
    method: 'PUT',
    body: { value },
  });
}

/** Remove a stored secret (e.g. to reset / re-enter an API key). */
export async function deleteSecret(secretKey: SecretKey): Promise<void> {
  await api(`/api/secrets/${secretKey}`, {
    method: 'DELETE',
  });
}
