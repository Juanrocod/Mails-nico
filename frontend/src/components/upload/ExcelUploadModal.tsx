import { useRef, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import type { PreviewCiclo } from "../../types/domain";

interface Props {
  open: boolean;
  onClose: () => void;
  onPreview: (file: File) => Promise<PreviewCiclo>;
  onConfirmar: (file: File) => void;
  isLoading: boolean;
}

export function ExcelUploadModal({ open, onClose, onPreview, onConfirmar, isLoading }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewCiclo | null>(null);
  const [error, setError] = useState("");

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setPreview(null);
    setError("");
  }

  async function handlePreview() {
    if (!file) return;
    setError("");
    try {
      const data = await onPreview(file);
      setPreview(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error al procesar");
    }
  }

  function handleConfirmar() {
    if (!file) return;
    onConfirmar(file);
    onClose();
  }

  function handleClose() {
    setFile(null);
    setPreview(null);
    setError("");
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Nuevo Ciclo de Envío</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx,.xls"
            className="hidden"
            onChange={handleFileChange}
          />
          <Button variant="outline" className="w-full" onClick={() => inputRef.current?.click()}>
            {file ? file.name : "Seleccionar Excel de deudores"}
          </Button>

          {file && !preview && (
            <Button className="w-full" onClick={handlePreview} disabled={isLoading}>
              {isLoading ? "Procesando..." : "Ver preview"}
            </Button>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}

          {preview && (
            <div className="rounded border p-4 space-y-2 bg-gray-50">
              <h3 className="font-semibold text-sm">Resumen del ciclo</h3>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <span className="text-gray-600">Para enviar:</span>
                <span className="font-medium text-green-700">{preview.para_enviar}</span>
                <span className="text-gray-600">Sin email:</span>
                <span className="font-medium text-amber-600">{preview.sin_email}</span>
                <span className="text-gray-600">Filtrados:</span>
                <span className="font-medium text-gray-500">{preview.filtrados}</span>
                <span className="text-gray-600">Total deudores:</span>
                <span className="font-medium">{preview.total_deudores}</span>
              </div>
              <div className="flex gap-2 pt-2">
                <Button variant="outline" className="flex-1" onClick={() => setPreview(null)}>
                  Volver
                </Button>
                <Button className="flex-1" onClick={handleConfirmar}>
                  Confirmar envío
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
