import { apiFetch } from "./api";

export async function refrescarSeguimiento(): Promise<void> {
  const r = await apiFetch("/seguimiento/refrescar", { method: "POST" });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al refrescar el seguimiento");
  }
}
