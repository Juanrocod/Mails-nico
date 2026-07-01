const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export function getAccessToken(): string | null {
  return localStorage.getItem("access_token");
}

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getAccessToken();
  const headers: HeadersInit = {
    ...(options.headers ?? {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  return fetch(`${BASE_URL}${path}`, { ...options, headers });
}
