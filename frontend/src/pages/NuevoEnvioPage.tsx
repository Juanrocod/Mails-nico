import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Button } from "../components/ui/button";
import { ExcelUploadModal } from "../components/upload/ExcelUploadModal";
import { ProgresoEnvio } from "../components/upload/ProgresoEnvio";
import { useCiclo } from "../hooks/useCiclo";
import { useState } from "react";
import type { Envio } from "../types/domain";

const PATH_TO_TAB: Record<string, string> = {
  "/nuevo-envio/para-enviar": "para_enviar",
  "/nuevo-envio/sin-email": "sin_email",
  "/nuevo-envio/filtrados": "filtrados",
};

export default function NuevoEnvioPage() {
  const { enviosActivo, preview, confirmar, isLoading, progreso, loadEnviosActivo } = useCiclo();
  const [modalOpen, setModalOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const activeTab = PATH_TO_TAB[location.pathname] ?? "para_enviar";

  useEffect(() => {
    loadEnviosActivo();
  }, [loadEnviosActivo]);

  const paraEnviar = enviosActivo.filter((e) => e.estado === "NO_CONTESTADO" && e.email);
  const sinEmail = enviosActivo.filter((e) => e.estado === "SIN_EMAIL");
  const filtrados = enviosActivo.filter((e) => e.estado === "FILTRADO");

  function handleTabChange(value: string) {
    const paths: Record<string, string> = {
      para_enviar: "/nuevo-envio/para-enviar",
      sin_email: "/nuevo-envio/sin-email",
      filtrados: "/nuevo-envio/filtrados",
    };
    navigate(paths[value] ?? "/nuevo-envio/para-enviar");
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Nuevo Envío</h1>
        <Button onClick={() => setModalOpen(true)}>Subir Excel de deudores</Button>
      </div>

      {progreso && isLoading && (
        <div className="rounded border p-4 bg-blue-50">
          <ProgresoEnvio enviado={progreso.enviado} total={progreso.total} />
        </div>
      )}

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="para_enviar">Para enviar ({paraEnviar.length})</TabsTrigger>
          <TabsTrigger value="sin_email">Sin Email ({sinEmail.length})</TabsTrigger>
          <TabsTrigger value="filtrados">Filtrados ({filtrados.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="para_enviar">
          <EnvioTable envios={paraEnviar} />
        </TabsContent>
        <TabsContent value="sin_email">
          <EnvioTable envios={sinEmail} />
        </TabsContent>
        <TabsContent value="filtrados">
          <EnvioTable envios={filtrados} showMotivo />
        </TabsContent>
      </Tabs>

      <ExcelUploadModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onPreview={preview}
        onConfirmar={(file) => confirmar(file)}
        isLoading={isLoading}
      />
    </div>
  );
}

function EnvioTable({ envios, showMotivo }: { envios: Envio[]; showMotivo?: boolean }) {
  if (envios.length === 0) {
    return <p className="text-sm text-gray-500 py-4">Sin registros en esta categoría.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-gray-600">
            <th className="py-2 pr-4">Consorcio</th>
            <th className="py-2 pr-4">Email</th>
            <th className="py-2 pr-4">Monto</th>
            {showMotivo && <th className="py-2">Motivo</th>}
          </tr>
        </thead>
        <tbody>
          {envios.map((e) => (
            <tr key={e.id} className="border-b hover:bg-gray-50">
              <td className="py-2 pr-4">{e.nombre_consorcio}</td>
              <td className="py-2 pr-4 text-gray-600">{e.email ?? "—"}</td>
              <td className="py-2 pr-4">${Number(e.monto).toLocaleString("es-AR")}</td>
              {showMotivo && <td className="py-2 text-xs text-gray-500">{e.motivo_filtrado ?? "—"}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
