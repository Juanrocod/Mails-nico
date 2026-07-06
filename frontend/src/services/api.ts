const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export function getAccessToken(): string | null {
  return localStorage.getItem("access_token");
}

function clearTokensAndRedirect() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) return null;
  try {
    const r = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!r.ok) return null;
    const data = await r.json();
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    return data.access_token as string;
  } catch {
    return null;
  }
}

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getAccessToken();
  const headers: HeadersInit = {
    ...(options.headers ?? {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const response = await fetch(`${BASE_URL}${path}`, { cache: "no-store", ...options, headers });

  const isAuthEndpoint = path === "/auth/login" || path === "/auth/refresh";
  if (response.status === 401 && !isAuthEndpoint) {
    const newToken = await refreshAccessToken();
    if (!newToken) {
      clearTokensAndRedirect();
      return response;
    }
    const retryResponse = await fetch(`${BASE_URL}${path}`, {
      cache: "no-store",
      ...options,
      headers: { ...(options.headers ?? {}), Authorization: `Bearer ${newToken}` },
    });
    if (retryResponse.status === 401) {
      clearTokensAndRedirect();
    }
    return retryResponse;
  }

  return response;
}
