import { useEffect, useState } from "react";
import { Pencil, Check, X, Trash2, RotateCcw } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { MaestroUploadModal } from "../components/upload/MaestroUploadModal";
import { AgregarClienteModal } from "../components/maestro/AgregarClienteModal";
import { getMaestro, updateCliente, uploadMaestro } from "../services/maestro";
import type { ClienteMaestro } from "../types/domain";

type EditForm = {
  nombre: string;
  email: string;
  prefiere_no_recibir_email: boolean;
};

function esInactivo(c: ClienteMaestro): boolean {
  return !c.activo || c.prefiere_no_recibir_email;
}

function motivoInactivo(c: ClienteMaestro): string {
  const motivos: string[] = [];
  if (c.prefiere_no_recibir_email) motivos.push("Baja");
  if (!c.activo) motivos.push("Eliminado");
  return motivos.join(" + ");
}

export default function MaestroPage() {
  const [clientes, setClientes] = useState<ClienteMaestro[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [agregarModalOpen, setAgregarModalOpen] = useState(false);
  const [mostrarInactivos, setMostrarInactivos] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditForm | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getMaestro().then(setClientes).catch(console.error);
  }, []);

  async function handleUpload(file: File) {
    const r = await uploadMaestro(file);
    getMaestro().then(setClientes).catch(console.error);
    return r;
  }

  function startEdit(c: ClienteMaestro) {
    setEditingId(c.id);
    setEditForm({
      nombre: c.nombre,
      email: c.email ?? "",
      prefiere_no_recibir_email: c.prefiere_no_recibir_email,
    });
    setError("");
  }

  function cancelEdit() {
    setEditingId(null);
    setEditForm(null);
    setError("");
  }

  async function saveEdit(id: string) {
    if (!editForm) return;
    setSaving(true);
    setError("");
    try {
      const updated = await updateCliente(id, editForm);
      setClientes((prev) => prev.map((c) => (c.id === id ? updated : c)));
      setEditingId(null);
      setEditForm(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error guardando el cliente");
    } finally {
      setSaving(false);
    }
  }

  async function handleEliminar(c: ClienteMaestro) {
    if (!window.confirm(`¿Eliminar a ${c.nombre}? Vas a poder reactivarlo despues desde "Mostrar inactivos".`)) {
      return;
    }
    setError("");
    try {
      const updated = await updateCliente(c.id, { activo: false });
      setClientes((prev) => prev.map((x) => (x.id === c.id ? updated : x)));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error eliminando el cliente");
    }
  }

  async function handleReactivar(c: ClienteMaestro) {
    setError("");
    try {
      const updated = await updateCliente(c.id, { activo: true, prefiere_no_recibir_email: false });
      setClientes((prev) => prev.map((x) => (x.id === c.id ? updated : x)));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error reactivando el cliente");
    }
  }

  function handleClienteCreado(cliente: ClienteMaestro) {
    setClientes((prev) =>
      [...prev, cliente].sort((a, b) => a.clave_union.localeCompare(b.clave_union)),
    );
  }

  const clientesVisibles = clientes.filter((c) => esInactivo(c) === mostrarInactivos);

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-baseline gap-3">
          <h1 className="text-xl font-semibold text-foreground">Maestro de Clientes</h1>
          <span className="text-sm text-muted-foreground">
            {clientesVisibles.length} clientes {mostrarInactivos ? "inactivos" : "registrados"}
          </span>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setAgregarModalOpen(true)}>
            Agregar cliente
          </Button>
          <Button onClick={() => setModalOpen(true)}>Actualizar Maestro</Button>
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm text-muted-foreground">
        <input
          type="checkbox"
          checked={mostrarInactivos}
          onChange={(e) => setMostrarInactivos(e.target.checked)}
          className="h-4 w-4 rounded border-border"
        />
        Mostrar inactivos
      </label>

      <MaestroUploadModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onUpload={handleUpload}
      />

      <AgregarClienteModal
        open={agregarModalOpen}
        onClose={() => setAgregarModalOpen(false)}
        onCreated={handleClienteCreado}
      />

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="overflow-x-auto">
        <table className="w-full text-sm table-fixed">
          <colgroup>
            <col className="w-28" />
            <col className="w-64" />
            <col className="w-72" />
            <col className="w-20" />
            <col className="w-16" />
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
                {mostrarInactivos ? "Motivo" : "Baja"}
              </th>
              <th aria-hidden />
            </tr>
          </thead>
          <tbody>
            {clientesVisibles.map((c) => {
              const isEditing = editingId === c.id;
              return (
                <tr key={c.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                  <td className="py-2.5 pr-6 font-mono text-xs text-muted-foreground truncate">
                    {c.clave_union}
                  </td>
                  <td className="py-2.5 pr-6 text-foreground truncate">
                    {isEditing && editForm ? (
                      <Input
                        value={editForm.nombre}
                        onChange={(e) => setEditForm({ ...editForm, nombre: e.target.value })}
                        className="h-8"
                      />
                    ) : (
                      c.nombre
                    )}
                  </td>
                  <td className="py-2.5 pr-6 text-muted-foreground truncate">
                    {isEditing && editForm ? (
                      <Input
                        type="email"
                        value={editForm.email}
                        onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                        className="h-8"
                      />
                    ) : (
                      c.email ?? "—"
                    )}
                  </td>
                  <td className="py-2.5 text-muted-foreground">
                    {mostrarInactivos ? (
                      motivoInactivo(c)
                    ) : isEditing && editForm ? (
                      <input
                        type="checkbox"
                        checked={editForm.prefiere_no_recibir_email}
                        onChange={(e) =>
                          setEditForm({ ...editForm, prefiere_no_recibir_email: e.target.checked })
                        }
                        className="h-4 w-4 rounded border-border"
                      />
                    ) : c.prefiere_no_recibir_email ? (
                      "Sí"
                    ) : (
                      "No"
                    )}
                  </td>
                  <td className="py-2.5">
                    {isEditing ? (
                      <div className="flex gap-1">
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8"
                          disabled={saving}
                          onClick={() => saveEdit(c.id)}
                          aria-label="Guardar"
                        >
                          <Check className="h-4 w-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8"
                          disabled={saving}
                          onClick={cancelEdit}
                          aria-label="Cancelar"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ) : !esInactivo(c) ? (
                      <div className="flex gap-1">
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8"
                          onClick={() => startEdit(c)}
                          aria-label="Editar"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8"
                          onClick={() => handleEliminar(c)}
                          aria-label="Eliminar"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ) : (
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8"
                        onClick={() => handleReactivar(c)}
                        aria-label="Reactivar"
                      >
                        <RotateCcw className="h-4 w-4" />
                      </Button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
