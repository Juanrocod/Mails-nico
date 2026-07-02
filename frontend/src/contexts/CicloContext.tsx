import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { useCiclo } from "../hooks/useCiclo";
import { ExcelUploadModal } from "../components/upload/ExcelUploadModal";
import { CicloContext } from "./ciclo-context-object";

export function CicloProvider({ children }: { children: ReactNode }) {
  const ciclo = useCiclo();
  const [modalOpen, setModalOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <CicloContext.Provider value={{ ...ciclo, openUpload: () => setModalOpen(true) }}>
      {children}
      <ExcelUploadModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onPreview={ciclo.preview}
        onReview={() => {
          navigate("/nuevo-envio/para-enviar");
          setModalOpen(false);
        }}
        isLoading={ciclo.isLoading}
      />
    </CicloContext.Provider>
  );
}
