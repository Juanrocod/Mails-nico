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
    <div className="p-6 max-w-sm space-y-4">
      <h1 className="text-2xl font-bold">Configuración</h1>
      <div className="space-y-3">
        <label className="block text-sm font-medium">Contraseña actual</label>
        <Input
          type="password"
          value={oldPass}
          onChange={(e) => setOldPass(e.target.value)}
        />
        <label className="block text-sm font-medium">Nueva contraseña</label>
        <Input
          type="password"
          value={newPass}
          onChange={(e) => setNewPass(e.target.value)}
        />
      </div>
      {status && <p className="text-sm text-gray-600">{status}</p>}
      <Button onClick={handleChange}>Cambiar contraseña</Button>
    </div>
  );
}
