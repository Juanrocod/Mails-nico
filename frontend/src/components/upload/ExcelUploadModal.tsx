import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { FileDropzone } from "./FileDropzone";
import type { PreviewCiclo } from "../../types/domain";
import { cn } from "../../lib/utils";

interface Props {
  open: boolean;
  onClose: () => void;
  onPreview: (file: File) => Promise<PreviewCiclo>;
  onReview: () => void;
  isLoading: boolean;
}

export function ExcelUploadModal({ open, onClose, onPreview, onReview, isLoading }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewCiclo | null>(null);
  const [error, setError] = useState("");

  function selectFile(f: File) {
    if (!f.name.match(/\.(xlsx|xls)$/i)) {
      setError("Solo se aceptan archivos .xlsx o .xls");
      return;
    }
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
          <FileDropzone file={file} onSelect={selectFile} />

          {file && !preview && (
            <Button className="w-full" onClick={handlePreview} disabled={isLoading}>
              {isLoading ? "Procesando..." : "Ver preview"}
            </Button>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}

          {preview && (
            <div className="rounded-md border border-border bg-secondary/40 p-4 space-y-3">
              <h3 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Resumen del ciclo
              </h3>
              <div className="grid grid-cols-2 gap-y-2 text-sm">
                <SummaryRow label="Para enviar" value={preview.para_enviar} dot="bg-success" />
                <SummaryRow label="Sin email" value={preview.sin_email} dot="bg-warning" />
                <SummaryRow label="Filtrados" value={preview.filtrados} dot="bg-muted-foreground" />
                <span className="text-muted-foreground">Total deudores</span>
                <span className="text-right tabular-nums font-medium text-foreground">
                  {preview.total_deudores}
                </span>
              </div>

              <div className="flex gap-2 pt-2">
                <Button variant="outline" className="flex-1" onClick={() => setPreview(null)}>
                  Volver
                </Button>
                <Button className="flex-1" onClick={onReview}>
                  Ver detalle
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function SummaryRow({ label, value, dot }: { label: string; value: number; dot: string }) {
  return (
    <>
      <span className="inline-flex items-center gap-1.5 text-muted-foreground">
        <span className={cn("h-1.5 w-1.5 rounded-full", dot)} aria-hidden />
        {label}
      </span>
      <span className="text-right tabular-nums font-medium text-foreground">{value}</span>
    </>
  );
}
