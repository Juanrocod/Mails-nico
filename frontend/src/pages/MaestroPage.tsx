import { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { getMaestro, uploadMaestro } from "../services/maestro";
import type { ClienteMaestro } from "../types/domain";

export default function MaestroPage() {
  const [clientes, setClientes] = useState<ClienteMaestro[]>([]);
  const [status, setStatus] = useState("");

  useEffect(() => {
    getMaestro().then(setClientes).catch(console.error);
  }, []);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setStatus("Subiendo...");
    try {
      const r = await uploadMaestro(file);
      setStatus(`Listo: ${r.nuevos} nuevos, ${r.actualizados} actualizados`);
      getMaestro().then(setClientes);
    } catch {
      setStatus("Error al subir el archivo");
    }
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Maestro de Clientes</h1>
        <label>
          <input type="file" accept=".xlsx,.xls" className="hidden" onChange={handleUpload} />
          <Button asChild><span>Actualizar Maestro</span></Button>
        </label>
      </div>
      {status && <p className="text-sm text-gray-600">{status}</p>}
      <p className="text-sm text-gray-500">{clientes.length} clientes registrados</p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-gray-600">
              <th className="py-2 pr-4">Clave</th>
              <th className="py-2 pr-4">Nombre</th>
              <th className="py-2 pr-4">Email</th>
              <th className="py-2">Baja</th>
            </tr>
          </thead>
          <tbody>
            {clientes.map((c) => (
              <tr key={c.id} className="border-b hover:bg-gray-50">
                <td className="py-2 pr-4 font-mono text-xs">{c.clave_union}</td>
                <td className="py-2 pr-4">{c.nombre}</td>
                <td className="py-2 pr-4 text-gray-600">{c.email ?? "—"}</td>
                <td className="py-2">{c.prefiere_no_recibir_email ? "Sí" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
