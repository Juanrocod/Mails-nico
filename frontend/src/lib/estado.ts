import type { MotivoFiltrado, EstadoEnvio } from "../types/domain";

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
