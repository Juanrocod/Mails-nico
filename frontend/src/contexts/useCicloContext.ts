import { useContext } from "react";
import { CicloContext } from "./ciclo-context-object";

export function useCicloContext() {
  const ctx = useContext(CicloContext);
  if (!ctx) throw new Error("useCicloContext debe usarse dentro de CicloProvider");
  return ctx;
}
