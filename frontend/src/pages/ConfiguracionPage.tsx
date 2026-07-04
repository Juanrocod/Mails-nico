import { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  getConfiguracionYahoo,
  updateConfiguracionYahoo,
  getConfiguracionGmail,
  updateConfiguracionGmail,
  getProveedorActivo,
  updateProveedorActivo,
} from "../services/configuracion";
import type { ProveedorEmail } from "../types/domain";

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
  }, []);

  async function handleCambiarProveedor(nuevo: ProveedorEmail) {
    setProveedor(nuevo);
    setProveedorStatus("Guardando...");
    try {
      await updateProveedorActivo(nuevo);
      setProveedorStatus("Guardado correctamente");
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
            <div>
              <h2 className="text-sm font-semibold text-foreground">Cuenta de Yahoo</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {yahooConfigurado
                  ? "Configurada — cargá una nueva clave para reemplazarla."
                  : "Sin configurar. El sistema no puede enviar ni leer mails hasta que cargues esto."}
              </p>
            </div>
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
            <div>
              <h2 className="text-sm font-semibold text-foreground">Cuenta de Gmail</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {gmailConfigurado
                  ? "Configurada — cargá una nueva clave para reemplazarla."
                  : "Sin configurar. El sistema no puede enviar ni leer mails hasta que cargues esto."}
              </p>
            </div>
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
