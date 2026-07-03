import { apiFetch } from "./api";
import type { Plantilla } from "../types/domain";

export async function getPlantilla(): Promise<Plantilla> {
  const r = await apiFetch("/plantilla");
  if (!r.ok) throw new Error("Error cargando plantilla");
  return r.json();
}

export async function updatePlantilla(data: Plantilla): Promise<Plantilla> {
  const r = await apiFetch("/plantilla", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) throw new Error("Error guardando plantilla");
  return r.json();
}

export async function uploadLogo(file: File): Promise<Plantilla> {
  const form = new FormData();
  form.append("file", file);
  const r = await apiFetch("/plantilla/logo", { method: "POST", body: form });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error subiendo el logo");
  }
  return r.json();
}
