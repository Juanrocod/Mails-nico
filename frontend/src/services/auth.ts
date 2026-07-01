import { apiFetch } from "./api";

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const r = await apiFetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) throw new Error("Credenciales inválidas");
  const data = await r.json();
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  return data;
}

export async function logout(): Promise<void> {
  await apiFetch("/auth/logout", { method: "POST" });
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  const r = await apiFetch("/auth/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al cambiar contraseña");
  }
}
