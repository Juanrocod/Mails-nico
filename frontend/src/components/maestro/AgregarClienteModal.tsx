import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { createCliente } from "../../services/maestro";
import type { ClienteMaestro } from "../../types/domain";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (cliente: ClienteMaestro) => void;
}

export function AgregarClienteModal({ open, onClose, onCreated }: Props) {
  const [claveUnion, setClaveUnion] = useState("");
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [localidad, setLocalidad] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  function reset() {
    setClaveUnion("");
    setNombre("");
    setEmail("");
    setLocalidad("");
    setError("");
  }

  function handleClose() {
    reset();
    onClose();
  }

  async function handleCrear() {
    setIsLoading(true);
    setError("");
    try {
      const cliente = await createCliente({
        clave_union: claveUnion,
        nombre,
        email: email || undefined,
        localidad: localidad || undefined,
      });
      onCreated(cliente);
      handleClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error creando el cliente");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Agregar cliente</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-foreground">Clave de unión</label>
            <Input value={claveUnion} onChange={(e) => setClaveUnion(e.target.value)} placeholder="C001" />
          </div>
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-foreground">Nombre</label>
            <Input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Consorcio X" />
          </div>
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-foreground">Email</label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="consorcio@mail.com"
            />
          </div>
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-foreground">Localidad</label>
            <Input value={localidad} onChange={(e) => setLocalidad(e.target.value)} placeholder="CABA" />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button
            className="w-full"
            onClick={handleCrear}
            disabled={isLoading || !claveUnion.trim() || !nombre.trim()}
          >
            {isLoading ? "Creando..." : "Crear cliente"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
