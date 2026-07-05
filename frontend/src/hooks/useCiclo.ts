import { useState, useCallback } from "react";
import { previewCiclo, confirmarCiclo, getEnviosActivo } from "../services/ciclos";
import type { Envio, PreviewCiclo } from "../types/domain";

export function useCiclo() {
  const [enviosActivo, setEnviosActivo] = useState<Envio[]>([]);
  const [previewData, setPreviewData] = useState<PreviewCiclo | null>(null);
  const [previewFile, setPreviewFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [progreso, setProgreso] = useState<{ enviado: number; total: number } | null>(null);
  const [confirmError, setConfirmError] = useState("");

  const loadEnviosActivo = useCallback(async () => {
    const data = await getEnviosActivo();
    setEnviosActivo(data);
  }, []);

  const preview = useCallback(async (file: File) => {
    setIsLoading(true);
    try {
      const data = await previewCiclo(file);
      setPreviewData(data);
      setPreviewFile(file);
      return data;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clearPreview = useCallback(() => {
    setPreviewData(null);
    setPreviewFile(null);
  }, []);

  const confirmar = useCallback(
    async (file: File, onDone?: () => void) => {
      setIsLoading(true);
      setProgreso({ enviado: 0, total: 0 });
      setConfirmError("");
      const cancel = confirmarCiclo(file, (data) => {
        if (data.done) {
          setIsLoading(false);
          setProgreso(null);
          if (data.error) setConfirmError(data.error);
          loadEnviosActivo();
          onDone?.();
        } else {
          setProgreso({ enviado: data.enviado, total: data.total });
        }
      });
      return cancel;
    },
    [loadEnviosActivo],
  );

  const confirmarPreview = useCallback(
    (onDone?: () => void) => {
      if (!previewFile) return;
      const file = previewFile;
      clearPreview();
      confirmar(file, onDone);
    },
    [previewFile, clearPreview, confirmar],
  );

  return {
    enviosActivo,
    previewData,
    previewFile,
    preview,
    clearPreview,
    confirmar,
    confirmarPreview,
    isLoading,
    progreso,
    confirmError,
    loadEnviosActivo,
  };
}
