import { apiFetch } from "./api";
import type { ConfiguracionYahoo, ConfiguracionGmail, ConfiguracionProveedor, ProveedorEmail } from "../types/domain";

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

export async function getConfiguracionGmail(): Promise<ConfiguracionGmail> {
  const r = await apiFetch("/configuracion/gmail");
  if (!r.ok) throw new Error("Error cargando configuración de Gmail");
  return r.json();
}

export async function updateConfiguracionGmail(
  gmail_email: string,
  gmail_app_password: string,
): Promise<ConfiguracionGmail> {
  const r = await apiFetch("/configuracion/gmail", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ gmail_email, gmail_app_password }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error guardando la configuración de Gmail");
  }
  return r.json();
}

export async function getProveedorActivo(): Promise<ConfiguracionProveedor> {
  const r = await apiFetch("/configuracion/proveedor");
  if (!r.ok) throw new Error("Error cargando el proveedor activo");
  return r.json();
}

export async function updateProveedorActivo(proveedor: ProveedorEmail): Promise<ConfiguracionProveedor> {
  const r = await apiFetch("/configuracion/proveedor", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ proveedor }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error guardando el proveedor activo");
  }
  return r.json();
}
