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
