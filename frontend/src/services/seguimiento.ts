import { apiFetch } from "./api";
import type { RespuestasTardias } from "../types/domain";

export async function refrescarSeguimiento(): Promise<void> {
  const r = await apiFetch("/seguimiento/refrescar", { method: "POST" });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al refrescar el seguimiento");
  }
}

export async function getRespuestasTardias(): Promise<RespuestasTardias> {
  const r = await apiFetch("/seguimiento/respuestas-tardias");
  if (!r.ok) throw new Error("Error cargando respuestas tardías");
  return r.json();
}
