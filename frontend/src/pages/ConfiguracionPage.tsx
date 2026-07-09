import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  getConfiguracionYahoo,
  updateConfiguracionYahoo,
  getConfiguracionGmail,
  updateConfiguracionGmail,
  getProveedorActivo,
  updateProveedorActivo,
  getEnviosPendientes,
  probarConexion,
} from "../services/configuracion";
import type {
  ConfiguracionEnviosPendientes,
  ConfiguracionProbarConexion,
  ProveedorEmail,
} from "../types/domain";

const DISMISS_KEY = "config_intrackeados_dismissed";

function intrackeadosSignature(data: ConfiguracionEnviosPendientes): string {
  return `${data.intrackeados_otro_proveedor}:${data.otro_proveedor_email ?? ""}`;
}

export default function ConfiguracionPage() {
  const [proveedor, setProveedor] = useState<ProveedorEmail>("yahoo");
  const [proveedorStatus, setProveedorStatus] = useState("");

  const [yahooEmail, setYahooEmail] = useState("");
  const [yahooPassword, setYahooPassword] = useState("");
  const [yahooConfigurado, setYahooConfigurado] = useState(false);
  const [yahooStatus, setYahooStatus] = useState("");

  const [gmailEmail, setGmailEmail] = useState("");
  const [gmailPassword, setGmailPassword] = useState("");
  const [gmailConfigurado, setGmailConfigurado] = useState(false);
  const [gmailStatus, setGmailStatus] = useState("");

  const [enviosPendientes, setEnviosPendientes] = useState<ConfiguracionEnviosPendientes | null>(null);
  const [intrackeadosDismissed, setIntrackeadosDismissed] = useState(false);

  const [probando, setProbando] = useState(false);
  const [resultadoConexion, setResultadoConexion] = useState<ConfiguracionProbarConexion | null>(null);

  function cargarEnviosPendientes() {
    getEnviosPendientes()
      .then((data) => {
        setEnviosPendientes(data);
        setIntrackeadosDismissed(localStorage.getItem(DISMISS_KEY) === intrackeadosSignature(data));
      })
      .catch(() => {});
  }

  useEffect(() => {
    getProveedorActivo()
      .then((data) => setProveedor(data.proveedor))
      .catch(() => {});
    getConfiguracionYahoo()
      .then((data) => {
        setYahooConfigurado(data.configurado);
        if (data.yahoo_email) setYahooEmail(data.yahoo_email);
      })
      .catch(() => {});
    getConfiguracionGmail()
      .then((data) => {
        setGmailConfigurado(data.configurado);
        if (data.gmail_email) setGmailEmail(data.gmail_email);
      })
      .catch(() => {});
    cargarEnviosPendientes();
  }, []);

  function handleDismissIntrackeados() {
    if (!enviosPendientes) return;
    localStorage.setItem(DISMISS_KEY, intrackeadosSignature(enviosPendientes));
    setIntrackeadosDismissed(true);
  }

  async function handleProbarConexion() {
    setProbando(true);
    setResultadoConexion(null);
    try {
      setResultadoConexion(await probarConexion(proveedor));
    } catch {
      setResultadoConexion({
        configurado: true, smtp_ok: false, imap_ok: false,
        smtp_error: null, imap_error: null,
        error: "No se pudo probar la conexión (error de red o servidor).",
      });
    } finally {
      setProbando(false);
    }
  }

  async function handleCambiarProveedor(nuevo: ProveedorEmail) {
    setProveedor(nuevo);
    setResultadoConexion(null);
    setProveedorStatus("Guardando...");
    try {
      await updateProveedorActivo(nuevo);
      setProveedorStatus("Guardado correctamente");
      cargarEnviosPendientes();
    } catch (e: unknown) {
      setProveedorStatus(e instanceof Error ? e.message : "Error");
    }
  }

  async function handleGuardarYahoo() {
    setYahooStatus("Guardando...");
    try {
      const data = await updateConfiguracionYahoo(yahooEmail, yahooPassword);
      setYahooConfigurado(data.configurado);
      setYahooPassword("");
      setResultadoConexion(null);
      setYahooStatus("Guardado correctamente");
    } catch (e: unknown) {
      setYahooStatus(e instanceof Error ? e.message : "Error");
    }
  }

  async function handleGuardarGmail() {
    setGmailStatus("Guardando...");
    try {
      const data = await updateConfiguracionGmail(gmailEmail, gmailPassword);
      setGmailConfigurado(data.configurado);
      setGmailPassword("");
      setResultadoConexion(null);
      setGmailStatus("Guardado correctamente");
    } catch (e: unknown) {
      setGmailStatus(e instanceof Error ? e.message : "Error");
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Configuración</h1>
        <p className="text-sm text-muted-foreground mt-1">Proveedor y credenciales de la cuenta de email.</p>
      </div>

      {(proveedor === "yahoo" ? yahooConfigurado : gmailConfigurado) && (
        <div className="max-w-sm space-y-2 rounded-md border border-border bg-muted/40 px-3 py-2.5 text-sm">
          <div className="flex items-center justify-between gap-3">
            <span className="text-foreground">
              Credenciales guardadas:{" "}
              <span className="font-medium">{proveedor === "yahoo" ? yahooEmail : gmailEmail}</span>
            </span>
            <Button size="sm" variant="outline" onClick={handleProbarConexion} disabled={probando}>
              {probando ? "Probando..." : "Probar conexión"}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Guardadas no significa verificadas. Probá la conexión para confirmar que el login realmente funciona.
          </p>
          {resultadoConexion && (
            resultadoConexion.error || !resultadoConexion.configurado ? (
              <p className="rounded bg-destructive/10 px-2 py-1.5 text-xs text-destructive-text">
                {resultadoConexion.error ?? "No hay credenciales guardadas para este proveedor."}
              </p>
            ) : (
              <div className="space-y-1 rounded bg-background/60 px-2 py-1.5 text-xs">
                <div className={resultadoConexion.smtp_ok ? "text-success-text" : "text-destructive-text"}>
                  {resultadoConexion.smtp_ok ? "✓" : "✗"} Envío (SMTP)
                  {resultadoConexion.smtp_ok ? " — conecta" : `: ${resultadoConexion.smtp_error ?? "no conecta"}`}
                </div>
                <div className={resultadoConexion.imap_ok ? "text-success-text" : "text-destructive-text"}>
                  {resultadoConexion.imap_ok ? "✓" : "✗"} Lectura (IMAP)
                  {resultadoConexion.imap_ok ? " — conecta" : `: ${resultadoConexion.imap_error ?? "no conecta"}`}
                </div>
              </div>
            )
          )}
        </div>
      )}

      {enviosPendientes && enviosPendientes.pendientes_proveedor_activo > 0 && (
        <div className="max-w-sm rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning-text">
          Hay {enviosPendientes.pendientes_proveedor_activo} envío
          {enviosPendientes.pendientes_proveedor_activo === 1 ? "" : "s"} esperando respuesta con este proveedor.
          Si cambiás de proveedor ahora, el sistema deja de poder detectar esas respuestas.
        </div>
      )}

      {enviosPendientes && enviosPendientes.intrackeados_otro_proveedor > 0 && !intrackeadosDismissed && (
        <div className="max-w-sm flex items-start justify-between gap-2 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning-text">
          <span>
            {enviosPendientes.intrackeados_otro_proveedor} envío
            {enviosPendientes.intrackeados_otro_proveedor === 1 ? "" : "s"} sin poder rastrearse
            {enviosPendientes.otro_proveedor_email ? ` (se mandaron desde ${enviosPendientes.otro_proveedor_email})` : ""}.
            Volvé a activar ese proveedor si querés seguir el seguimiento.
          </span>
          <button
            type="button"
            onClick={handleDismissIntrackeados}
            aria-label="Cerrar aviso"
            className="shrink-0 text-warning-text/70 hover:text-warning-text"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="max-w-sm space-y-4">
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-foreground">Proveedor de email</label>
          <select
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            value={proveedor}
            onChange={(e) => handleCambiarProveedor(e.target.value as ProveedorEmail)}
          >
            <option value="yahoo">Yahoo</option>
            <option value="gmail">Gmail</option>
          </select>
          {proveedorStatus && <p className="text-sm text-muted-foreground">{proveedorStatus}</p>}
        </div>

        {proveedor === "yahoo" && (
          <div className="space-y-4">
            {!yahooConfigurado && (
              <p className="text-xs text-muted-foreground">
                Sin configurar. El sistema no puede enviar ni leer mails hasta que cargues esto.
              </p>
            )}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-foreground">Email de Yahoo</label>
              <Input
                type="email"
                value={yahooEmail}
                onChange={(e) => setYahooEmail(e.target.value)}
                placeholder="empresa@yahoo.com"
              />
            </div>
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-foreground">App password</label>
              <Input
                type="password"
                value={yahooPassword}
                onChange={(e) => setYahooPassword(e.target.value)}
                placeholder="Generada desde la cuenta de Yahoo (no la contraseña normal)"
              />
            </div>
            {yahooStatus && <p className="text-sm text-muted-foreground">{yahooStatus}</p>}
            <Button onClick={handleGuardarYahoo} disabled={!yahooEmail || !yahooPassword}>
              Guardar credenciales de Yahoo
            </Button>
          </div>
        )}

        {proveedor === "gmail" && (
          <div className="space-y-4">
            {!gmailConfigurado && (
              <p className="text-xs text-muted-foreground">
                Sin configurar. El sistema no puede enviar ni leer mails hasta que cargues esto.
              </p>
            )}
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-foreground">Email de Gmail</label>
              <Input
                type="email"
                value={gmailEmail}
                onChange={(e) => setGmailEmail(e.target.value)}
                placeholder="empresa@gmail.com"
              />
            </div>
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-foreground">App password</label>
              <Input
                type="password"
                value={gmailPassword}
                onChange={(e) => setGmailPassword(e.target.value)}
                placeholder="Requiere verificación en 2 pasos activada en la cuenta de Google"
              />
            </div>
            {gmailStatus && <p className="text-sm text-muted-foreground">{gmailStatus}</p>}
            <Button onClick={handleGuardarGmail} disabled={!gmailEmail || !gmailPassword}>
              Guardar credenciales de Gmail
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
