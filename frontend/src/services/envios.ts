import { apiFetch } from "./api";
import type { Envio } from "../types/domain";

export async function patchEnvioEstado(id: string, estado: "PAGO"): Promise<Envio> {
  const r = await apiFetch(`/envios/${id}/estado`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ estado }),
  });
  if (!r.ok) throw new Error("Error actualizando estado");
  return r.json();
}
