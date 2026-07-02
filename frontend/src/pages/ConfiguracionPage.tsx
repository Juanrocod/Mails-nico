import { useState } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { changePassword } from "../services/auth";

export default function ConfiguracionPage() {
  const [oldPass, setOldPass] = useState("");
  const [newPass, setNewPass] = useState("");
  const [status, setStatus] = useState("");

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
    </div>
  );
}
