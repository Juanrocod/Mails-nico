import { createContext } from "react";
import type { useCiclo } from "../hooks/useCiclo";

export type CicloContextValue = ReturnType<typeof useCiclo> & {
  openUpload: () => void;
};

export const CicloContext = createContext<CicloContextValue | null>(null);
