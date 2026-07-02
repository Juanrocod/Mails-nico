import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { FileDropzone } from "./FileDropzone";

interface Props {
  open: boolean;
  onClose: () => void;
  onUpload: (file: File) => Promise<{ nuevos: number; actualizados: number; total: number }>;
}

export function MaestroUploadModal({ open, onClose, onUpload }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<{ nuevos: number; actualizados: number; total: number } | null>(null);

  function selectFile(f: File) {
    if (!f.name.match(/\.(xlsx|xls)$/i)) {
      setError("Solo se aceptan archivos .xlsx o .xls");
      return;
    }
    setFile(f);
    setResult(null);
    setError("");
  }

  async function handleSubir() {
    if (!file) return;
    setIsLoading(true);
    setError("");
    try {
      const r = await onUpload(file);
      setResult(r);
    } catch {
      setError("Error al subir el archivo");
    } finally {
      setIsLoading(false);
    }
  }

  function handleClose() {
    setFile(null);
    setResult(null);
    setError("");
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Actualizar Maestro de Clientes</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <FileDropzone file={file} onSelect={selectFile} disabled={isLoading} />

          {error && <p className="text-sm text-destructive">{error}</p>}

          {result && (
            <div className="rounded-md border border-border bg-secondary/40 p-4 text-sm text-foreground">
              Listo: {result.nuevos} nuevos, {result.actualizados} actualizados de {result.total} clientes.
            </div>
          )}

          {file && !result && (
            <Button className="w-full" onClick={handleSubir} disabled={isLoading}>
              {isLoading ? "Subiendo..." : "Subir"}
            </Button>
          )}

          {result && (
            <Button className="w-full" onClick={handleClose}>
              Cerrar
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
