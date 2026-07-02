import { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { MaestroUploadModal } from "../components/upload/MaestroUploadModal";
import { getMaestro, uploadMaestro } from "../services/maestro";
import type { ClienteMaestro } from "../types/domain";

export default function MaestroPage() {
  const [clientes, setClientes] = useState<ClienteMaestro[]>([]);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    getMaestro().then(setClientes).catch(console.error);
  }, []);

  async function handleUpload(file: File) {
    const r = await uploadMaestro(file);
    getMaestro().then(setClientes).catch(console.error);
    return r;
  }

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-baseline gap-3">
          <h1 className="text-xl font-semibold text-foreground">Maestro de Clientes</h1>
          <span className="text-sm text-muted-foreground">
            {clientes.length} clientes registrados
          </span>
        </div>
        <Button onClick={() => setModalOpen(true)}>Actualizar Maestro</Button>
      </div>

      <MaestroUploadModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onUpload={handleUpload}
      />
      <div className="overflow-x-auto">
        <table className="w-full text-sm table-fixed">
          <colgroup>
            <col className="w-28" />
            <col className="w-64" />
            <col className="w-72" />
            <col className="w-20" />
            <col />
          </colgroup>
          <thead>
            <tr className="border-b border-border text-left">
              <th className="py-2 pr-6 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Clave
              </th>
              <th className="py-2 pr-6 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Nombre
              </th>
              <th className="py-2 pr-6 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Email
              </th>
              <th className="py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Baja
              </th>
              <th aria-hidden />
            </tr>
          </thead>
          <tbody>
            {clientes.map((c) => (
              <tr key={c.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                <td className="py-2.5 pr-6 font-mono text-xs text-muted-foreground truncate">
                  {c.clave_union}
                </td>
                <td className="py-2.5 pr-6 text-foreground truncate">{c.nombre}</td>
                <td className="py-2.5 pr-6 text-muted-foreground truncate">{c.email ?? "—"}</td>
                <td className="py-2.5 text-muted-foreground">
                  {c.prefiere_no_recibir_email ? "Sí" : "No"}
                </td>
                <td aria-hidden />
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
