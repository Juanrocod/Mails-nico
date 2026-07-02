export type EstadoEnvio =
  | "NO_CONTESTADO"
  | "CONTESTADO"
  | "PAGO"
  | "REBOTADO"
  | "SIN_EMAIL"
  | "FILTRADO";

export type MotivoFiltrado = "MONTO_MINIMO" | "DADO_DE_BAJA";

export interface Envio {
  id: string;
  ciclo_id: string;
  ciclo_numero: number;
  clave_union: string;
  nombre_consorcio: string;
  email: string | null;
  monto: number;
  estado: EstadoEnvio;
  motivo_filtrado: MotivoFiltrado | null;
  message_id: string | null;
  reply_snippet: string | null;
  enviado_en: string | null;
  actualizado_en: string;
}

export interface PreviewItem {
  clave_union: string;
  nombre_consorcio: string;
  email: string | null;
  monto: number;
  localidad: string | null;
  motivo_filtrado: MotivoFiltrado | null;
}

export interface PreviewCiclo {
  para_enviar: number;
  sin_email: number;
  filtrados: number;
  total_deudores: number;
  monto_total_enviar: number;
  items_para_enviar: PreviewItem[];
  items_sin_email: PreviewItem[];
  items_filtrados: PreviewItem[];
}

export interface ClienteMaestro {
  id: string;
  clave_union: string;
  nombre: string;
  email: string | null;
  localidad: string | null;
  prefiere_no_recibir_email: boolean;
  activo: boolean;
}

export interface Plantilla {
  asunto: string;
  cuerpo_html: string;
  nombre_empresa: string;
  logo_url: string | null;
  color_primario: string;
  monto_minimo: number;
}
