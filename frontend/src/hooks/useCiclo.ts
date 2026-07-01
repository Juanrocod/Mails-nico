import { useState, useCallback } from "react";
import { previewCiclo, confirmarCiclo, getEnviosActivo } from "../services/ciclos";
import type { Envio, PreviewCiclo } from "../types/domain";

export function useCiclo() {
  const [enviosActivo, setEnviosActivo] = useState<Envio[]>([]);
  const [previewData, setPreviewData] = useState<PreviewCiclo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [progreso, setProgreso] = useState<{ enviado: number; total: number } | null>(null);

  const loadEnviosActivo = useCallback(async () => {
    const data = await getEnviosActivo();
    setEnviosActivo(data);
  }, []);

  const preview = useCallback(async (file: File) => {
    setIsLoading(true);
    try {
      const data = await previewCiclo(file);
      setPreviewData(data);
      return data;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const confirmar = useCallback(
    async (file: File, onDone?: () => void) => {
      setIsLoading(true);
      setProgreso({ enviado: 0, total: 0 });
      const cancel = confirmarCiclo(file, (data) => {
        if (data.done) {
          setIsLoading(false);
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

  return { enviosActivo, previewData, preview, confirmar, isLoading, progreso, loadEnviosActivo };
}
