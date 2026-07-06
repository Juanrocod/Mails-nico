import { apiFetch } from "./api";
import type { DashboardResumen, EvolucionCiclo } from "../types/domain";

export async function getDashboardResumen(): Promise<DashboardResumen> {
  const r = await apiFetch("/dashboard/resumen");
  if (!r.ok) throw new Error("Error cargando el resumen del dashboard");
  return r.json();
}

export async function getDashboardEvolucion(): Promise<EvolucionCiclo[]> {
  const r = await apiFetch("/dashboard/evolucion");
  if (!r.ok) throw new Error("Error cargando la evolución");
  return r.json();
}
