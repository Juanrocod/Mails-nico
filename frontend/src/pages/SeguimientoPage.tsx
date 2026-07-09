import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { RefreshCw } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Button } from "../components/ui/button";
import { EnvioCard } from "../components/envios/EnvioCard";
import { EnvioDrawer } from "../components/envios/EnvioDrawer";
import { getEnviosActivo, getCiclos, getEnviosDeCiclo } from "../services/ciclos";
import { patchEnvioEstado } from "../services/envios";
import { refrescarSeguimiento, getRespuestasTardias } from "../services/seguimiento";
import type { Envio, CicloResumen, RespuestasTardias } from "../types/domain";

const PATH_TO_TAB: Record<string, string> = {
  "/seguimiento/no-contestados": "no_contestados",
  "/seguimiento/contestados": "contestados",
  "/seguimiento/pagos": "pagos",
  "/seguimiento/rebotados": "rebotados",
};

export default function SeguimientoPage() {
  const [envios, setEnvios] = useState<Envio[]>([]);
  const [selected, setSelected] = useState<Envio | null>(null);
  const [refrescando, setRefrescando] = useState(false);
  const [refrescarError, setRefrescarError] = useState("");
  const [ciclos, setCiclos] = useState<CicloResumen[]>([]);
  const [cicloSeleccionado, setCicloSeleccionado] = useState<string>("activo");
  const [tardias, setTardias] = useState<RespuestasTardias | null>(null);
  const [tardiasDismissed, setTardiasDismissed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const activeTab = PATH_TO_TAB[location.pathname] ?? "no_contestados";
  const cicloActivoSeleccionado = cicloSeleccionado === "activo";
  const numeroCicloSeleccionado = ciclos.find((c) => c.id === cicloSeleccionado)?.numero;
  const subtitulo = cicloActivoSeleccionado
    ? "Estado de respuesta de los mails del ciclo activo"
    : `Estado de respuesta de los mails del ciclo #${numeroCicloSeleccionado} (histórico)`;

  useEffect(() => {
    getEnviosActivo().then(setEnvios).catch(console.error);
    getCiclos().then(setCiclos).catch(console.error);
    getRespuestasTardias()
      .then((t) => {
        setTardias(t);
        const firma = `tardias:${t.count}`;
        setTardiasDismissed(localStorage.getItem("seg_tardias_dismissed") === firma);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (cicloSeleccionado === "activo") {
      getEnviosActivo().then(setEnvios).catch(console.error);
    } else {
      getEnviosDeCiclo(cicloSeleccionado).then(setEnvios).catch(console.error);
    }
  }, [cicloSeleccionado]);

  async function marcarPago(id: string) {
    const updated = await patchEnvioEstado(id, "PAGO");
    setEnvios((prev) => prev.map((e) => (e.id === id ? updated : e)));
  }

  async function handleRefrescar() {
    setRefrescando(true);
    setRefrescarError("");
    try {
      await refrescarSeguimiento();
      const data =
        cicloSeleccionado === "activo" ? await getEnviosActivo() : await getEnviosDeCiclo(cicloSeleccionado);
      setEnvios(data);
    } catch (e: unknown) {
      setRefrescarError(e instanceof Error ? e.message : "Error al refrescar el seguimiento");
    } finally {
      setRefrescando(false);
    }
  }

  function dismissTardias() {
    if (!tardias) return;
    localStorage.setItem("seg_tardias_dismissed", `tardias:${tardias.count}`);
    setTardiasDismissed(true);
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
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-baseline gap-3">
          <h1 className="text-xl font-semibold text-foreground">Seguimiento</h1>
          <span className="text-sm text-muted-foreground">{subtitulo}</span>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefrescar} disabled={refrescando}>
          <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${refrescando ? "animate-spin" : ""}`} />
          {refrescando ? "Revisando..." : "Refrescar ahora"}
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <label className="text-sm text-muted-foreground">Ciclo:</label>
        <select
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          value={cicloSeleccionado}
          onChange={(e) => setCicloSeleccionado(e.target.value)}
        >
          <option value="activo">Ciclo actual</option>
          {ciclos
            .filter((c) => !c.activo)
            .map((c) => (
              <option key={c.id} value={c.id}>
                Ciclo #{c.numero} — {new Date(c.creado_en).toLocaleDateString("es-AR")}
              </option>
            ))}
        </select>
      </div>

      {tardias && tardias.count > 0 && !tardiasDismissed && (
        <div className="flex items-start justify-between gap-2 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning-text">
          <span>
            {tardias.count} respuesta{tardias.count === 1 ? "" : "s"} nueva{tardias.count === 1 ? "" : "s"} en
            ciclos anteriores:{" "}
            {tardias.ciclos.map((c, idx) => (
              <button
                key={c.ciclo_id}
                type="button"
                className="underline"
                onClick={() => setCicloSeleccionado(c.ciclo_id)}
              >
                {idx > 0 ? ", " : ""}Ciclo #{c.numero} ({c.count})
              </button>
            ))}
          </span>
          <button type="button" onClick={dismissTardias} aria-label="Cerrar aviso" className="shrink-0">
            ✕
          </button>
        </div>
      )}

      {refrescarError && <p className="text-sm text-destructive">{refrescarError}</p>}

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
                {tab === "pagos" && list.length > 0 && (
                  <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                    Detectados automáticamente por traer un adjunto en la respuesta (probable comprobante), más
                    los que marcaste a mano. No es una confirmación de acreditación — revisá cada uno antes de
                    darlo por cobrado.
                  </p>
                )}
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
