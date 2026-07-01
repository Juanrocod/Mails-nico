import { useState, useCallback } from "react";
import { patchEnvioEstado } from "../services/envios";
import type { Envio } from "../types/domain";

export function useEnvios(initialEnvios: Envio[]) {
  const [envios, setEnvios] = useState<Envio[]>(initialEnvios);

  const patchEstado = useCallback(async (id: string, estado: "PAGO") => {
    const updated = await patchEnvioEstado(id, estado);
    setEnvios((prev) => prev.map((e) => (e.id === id ? updated : e)));
    return updated;
  }, []);

  return { envios, setEnvios, patchEstado };
}
