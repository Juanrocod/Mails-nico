import { apiFetch } from "./api";
import type { ClienteMaestro } from "../types/domain";

export async function uploadMaestro(file: File): Promise<{ nuevos: number; actualizados: number; total: number }> {
  const form = new FormData();
  form.append("file", file);
  const r = await apiFetch("/maestro/upload", { method: "POST", body: form });
  if (!r.ok) throw new Error("Error al subir maestro");
  return r.json();
}

export async function getMaestro(): Promise<ClienteMaestro[]> {
  const r = await apiFetch("/maestro");
  if (!r.ok) throw new Error("Error cargando maestro");
  return r.json();
}

export async function updateCliente(
  id: string,
  data: Partial<Pick<ClienteMaestro, "nombre" | "email" | "localidad" | "prefiere_no_recibir_email" | "activo">>
): Promise<ClienteMaestro> {
  const r = await apiFetch(`/maestro/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    const detail = Array.isArray(err.detail)
      ? err.detail.map((d: { msg?: string }) => d.msg).join("; ")
      : err.detail;
    throw new Error(detail ?? "Error guardando el cliente");
  }
  return r.json();
}

export async function createCliente(data: {
  clave_union: string;
  nombre: string;
  email?: string;
  localidad?: string;
}): Promise<ClienteMaestro> {
  const r = await apiFetch("/maestro", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    const detail = Array.isArray(err.detail)
      ? err.detail.map((d: { msg?: string }) => d.msg).join("; ")
      : err.detail;
    throw new Error(detail ?? "Error creando el cliente");
  }
  return r.json();
}
