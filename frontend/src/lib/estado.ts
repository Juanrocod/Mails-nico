import { differenceInDays } from "date-fns";
import type { MotivoFiltrado, EstadoEnvio } from "../types/domain";

export interface CategoriaRiesgo {
  label: string;
  badge: string;
}

// Antiguedad compacta: "12 dias" si es menos de un mes, si no "+N meses"
// (~30 dias por mes; el "+" indica "mas de N meses").
export function antiguedadCorta(dias: number): string {
  if (dias < 30) return `${dias} día${dias === 1 ? "" : "s"}`;
  const meses = Math.floor(dias / 30);
  return `+${meses} mes${meses === 1 ? "" : "es"}`;
}

// Semaforo de cobranza segun antiguedad de la deuda vigente (deudor_desde).
// Al dia (no debe) / Atraso leve (<=30d) / Moroso (31-90d) / Moroso cronico (>90d).
export function categoriaRiesgo(deudorDesde: string | null): CategoriaRiesgo {
  if (!deudorDesde) return { label: "Al día", badge: "bg-success/15 text-success-text" };
  const dias = differenceInDays(new Date(), new Date(deudorDesde));
  if (dias <= 30) return { label: "Atraso leve", badge: "bg-warning/15 text-warning-text" };
  if (dias <= 90) return { label: "Moroso", badge: "bg-orange/15 text-orange-text" };
  return { label: "Moroso crónico", badge: "bg-destructive/15 text-destructive-text" };
}

export const MOTIVO_LABEL: Record<MotivoFiltrado, string> = {
  MONTO_MINIMO: "Monto mínimo",
  DADO_DE_BAJA: "Dado de baja",
};

export const MOTIVO_DOT: Record<MotivoFiltrado, string> = {
  MONTO_MINIMO: "bg-warning",
  DADO_DE_BAJA: "bg-destructive",
};

export const ESTADO_LABEL: Partial<Record<EstadoEnvio, string>> = {
  NO_CONTESTADO: "No contestado",
  CONTESTADO: "Contestado",
  PAGO: "Pago",
  REBOTADO: "Rebotado",
};

export const ESTADO_DOT: Partial<Record<EstadoEnvio, string>> = {
  NO_CONTESTADO: "bg-muted-foreground/50",
  CONTESTADO: "bg-primary",
  PAGO: "bg-success",
  REBOTADO: "bg-destructive",
};

export const ESTADO_BADGE: Partial<Record<EstadoEnvio, string>> = {
  NO_CONTESTADO: "bg-muted text-muted-foreground",
  CONTESTADO: "bg-primary/10 text-primary",
  PAGO: "bg-success/15 text-success-text",
  REBOTADO: "bg-destructive/10 text-destructive-text",
};
