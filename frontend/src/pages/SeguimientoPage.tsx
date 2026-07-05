import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { EnvioCard } from "../components/envios/EnvioCard";
import { EnvioDrawer } from "../components/envios/EnvioDrawer";
import { getEnviosActivo } from "../services/ciclos";
import { patchEnvioEstado } from "../services/envios";
import type { Envio } from "../types/domain";

const PATH_TO_TAB: Record<string, string> = {
  "/seguimiento/no-contestados": "no_contestados",
  "/seguimiento/contestados": "contestados",
  "/seguimiento/pagos": "pagos",
  "/seguimiento/rebotados": "rebotados",
};

export default function SeguimientoPage() {
  const [envios, setEnvios] = useState<Envio[]>([]);
  const [selected, setSelected] = useState<Envio | null>(null);
  const location = useLocation();
  const navigate = useNavigate();

  const activeTab = PATH_TO_TAB[location.pathname] ?? "no_contestados";

  useEffect(() => {
    getEnviosActivo().then(setEnvios).catch(console.error);
  }, []);

  async function marcarPago(id: string) {
    const updated = await patchEnvioEstado(id, "PAGO");
    setEnvios((prev) => prev.map((e) => (e.id === id ? updated : e)));
  }

  function handleTabChange(value: string) {
    const paths: Record<string, string> = {
      no_contestados: "/seguimiento/no-contestados",
      contestados: "/seguimiento/contestados",
      pagos: "/seguimiento/pagos",
      rebotados: "/seguimiento/rebotados",
    };
    navigate(paths[value] ?? "/seguimiento/no-contestados");
  }

  const noContestados = envios.filter((e) => e.estado === "NO_CONTESTADO" && e.message_id);
  const contestados = envios.filter((e) => e.estado === "CONTESTADO");
  const pagos = envios.filter((e) => e.estado === "PAGO");
  const rebotados = envios.filter((e) => e.estado === "REBOTADO");

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div className="flex items-baseline gap-3">
        <h1 className="text-xl font-semibold text-foreground">Seguimiento</h1>
        <span className="text-sm text-muted-foreground">
          Estado de respuesta de los mails del ciclo activo
        </span>
      </div>

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="no_contestados">
            No contestados ({noContestados.length})
          </TabsTrigger>
          <TabsTrigger value="contestados">
            Contestados ({contestados.length})
          </TabsTrigger>
          <TabsTrigger value="pagos">Pagos ({pagos.length})</TabsTrigger>
          <TabsTrigger value="rebotados">
            Rebotados ({rebotados.length})
          </TabsTrigger>
        </TabsList>

        {(
          ["no_contestados", "contestados", "pagos", "rebotados"] as const
        ).map((tab) => {
          const list =
            tab === "no_contestados"
              ? noContestados
              : tab === "contestados"
                ? contestados
                : tab === "pagos"
                  ? pagos
                  : rebotados;
          return (
            <TabsContent key={tab} value={tab}>
              <div className="space-y-3 mt-2">
                {list.length === 0 ? (
                  <div className="text-center py-16">
                    <p className="text-sm text-muted-foreground">Sin registros.</p>
                  </div>
                ) : (
                  list.map((e) => (
                    <EnvioCard
                      key={e.id}
                      envio={e}
                      onClick={() => setSelected(e)}
                    />
                  ))
                )}
              </div>
            </TabsContent>
          );
        })}
      </Tabs>

      <EnvioDrawer
        envio={selected}
        onClose={() => setSelected(null)}
        onMarcarPago={marcarPago}
      />
    </div>
  );
}
