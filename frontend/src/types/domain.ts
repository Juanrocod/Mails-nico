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
  reply_en: string | null;
  tiene_adjunto: boolean;
  enviado_en: string | null;
  saldado_en: string | null;
  actualizado_en: string;
  en_proceso: boolean;
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
  nuevos: number;
  repiten: number;
  a_saldar: number;
  duplicados: number;
  total_ciclo_anterior: number;
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

export interface ConfiguracionYahoo {
  yahoo_email: string | null;
  configurado: boolean;
}

export type ProveedorEmail = "yahoo" | "gmail";

export interface ConfiguracionProveedor {
  proveedor: ProveedorEmail;
}

export interface ConfiguracionGmail {
  gmail_email: string | null;
  configurado: boolean;
}

export interface ConfiguracionEnviosPendientes {
  pendientes_proveedor_activo: number;
  intrackeados_otro_proveedor: number;
  otro_proveedor_email: string | null;
}

export interface DashboardResumen {
  hay_ciclo_activo: boolean;
  deuda_total: number;
  deuda_total_anterior: number | null;
  deudores: number;
  deudores_anterior: number | null;
  cobrado: number | null;
  efectividad: number | null;
}

export interface EvolucionCiclo {
  numero: number;
  fecha: string;
  deuda_total: number;
  deudores: number;
  cobrado: number | null;
}

export interface CicloResumen {
  id: string;
  numero: number;
  activo: boolean;
  creado_en: string;
  total_envios: number;
  deuda_total: number;
}

export interface HistorialItem {
  envio_id: string;
  ciclo: number;
  ciclo_activo: boolean;
  fecha: string;
  monto: number;
  estado: EstadoEnvio;
  motivo_filtrado: MotivoFiltrado | null;
  recibio_mail: boolean;
  reply_en: string | null;
  saldado_en: string | null;
  racha: number;
}

export interface HistorialCliente {
  cliente: ClienteMaestro | null;
  clave_union: string;
  items: HistorialItem[];
}

export interface RespuestasTardias {
  count: number;
  ciclos: { ciclo_id: string; numero: number; count: number }[];
}
