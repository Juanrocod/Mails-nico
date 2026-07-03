import { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { changePassword } from "../services/auth";
import { getConfiguracionYahoo, updateConfiguracionYahoo } from "../services/configuracion";

export default function ConfiguracionPage() {
  const [oldPass, setOldPass] = useState("");
  const [newPass, setNewPass] = useState("");
  const [status, setStatus] = useState("");

  const [yahooEmail, setYahooEmail] = useState("");
  const [yahooPassword, setYahooPassword] = useState("");
  const [yahooConfigurado, setYahooConfigurado] = useState(false);
  const [yahooStatus, setYahooStatus] = useState("");

  useEffect(() => {
    getConfiguracionYahoo()
      .then((data) => {
        setYahooConfigurado(data.configurado);
        if (data.yahoo_email) setYahooEmail(data.yahoo_email);
      })
      .catch(() => {});
  }, []);

  async function handleChange() {
    setStatus("Cambiando...");
    try {
      await changePassword(oldPass, newPass);
      setStatus("Contraseña cambiada correctamente");
      setOldPass("");
      setNewPass("");
    } catch (e: unknown) {
      setStatus(e instanceof Error ? e.message : "Error");
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

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Configuración</h1>
        <p className="text-sm text-muted-foreground mt-1">Cambiar la contraseña de acceso.</p>
      </div>

      <div className="max-w-sm space-y-4">
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-foreground">Contraseña actual</label>
          <Input
            type="password"
            value={oldPass}
            onChange={(e) => setOldPass(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-foreground">Nueva contraseña</label>
          <Input
            type="password"
            value={newPass}
            onChange={(e) => setNewPass(e.target.value)}
          />
        </div>
        {status && <p className="text-sm text-muted-foreground">{status}</p>}
        <Button onClick={handleChange}>Cambiar contraseña</Button>
      </div>

      <div className="max-w-sm space-y-4 pt-4 border-t border-border">
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
    </div>
  );
}
