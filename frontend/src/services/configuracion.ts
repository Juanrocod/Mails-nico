import { apiFetch } from "./api";
import type { ConfiguracionYahoo } from "../types/domain";

export async function getConfiguracionYahoo(): Promise<ConfiguracionYahoo> {
  const r = await apiFetch("/configuracion/yahoo");
  if (!r.ok) throw new Error("Error cargando configuración de Yahoo");
  return r.json();
}

export async function updateConfiguracionYahoo(
  yahoo_email: string,
  yahoo_app_password: string,
): Promise<ConfiguracionYahoo> {
  const r = await apiFetch("/configuracion/yahoo", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yahoo_email, yahoo_app_password }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error guardando la configuración de Yahoo");
  }
  return r.json();
}
