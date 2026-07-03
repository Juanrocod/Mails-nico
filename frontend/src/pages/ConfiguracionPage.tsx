import { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { getConfiguracionYahoo, updateConfiguracionYahoo } from "../services/configuracion";

export default function ConfiguracionPage() {
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
        <p className="text-sm text-muted-foreground mt-1">Credenciales de la cuenta de Yahoo.</p>
      </div>

      <div className="max-w-sm space-y-4">
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
