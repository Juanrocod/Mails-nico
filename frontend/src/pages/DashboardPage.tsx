import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { format, formatDistanceToNow, differenceInDays } from "date-fns";
import { es } from "date-fns/locale";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Skeleton } from "../components/ui/skeleton";
import { EvolucionChart } from "../components/dashboard/EvolucionChart";
import { getDashboardResumen, getDashboardEvolucion, getMorosos } from "../services/dashboard";
import { getEnviosActivo } from "../services/ciclos";
import type { DashboardResumen, EvolucionCiclo, Envio, Moroso } from "../types/domain";

function pesos(n: number | null): string {
  if (n === null) return "—";
  return `$${Number(n).toLocaleString("es-AR")}`;
}

function VariacionDeuda({ actual, anterior }: { actual: number; anterior: number | null }) {
  if (anterior === null || Number(anterior) === 0) return null;
  const pct = ((actual - anterior) / anterior) * 100;
  const bajo = pct < 0;
  const signo = pct > 0 ? "+" : "";
  return (
    <span className={bajo ? "text-success-text" : "text-destructive"}>
      {signo}{pct.toFixed(1)}% vs. ciclo anterior
    </span>
  );
}

function KpiCard({ titulo, valor, detalle }: { titulo: string; valor: string; detalle?: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border bg-secondary/30 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{titulo}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-foreground">{valor}</p>
      {detalle && <p className="mt-0.5 text-xs text-muted-foreground">{detalle}</p>}
    </div>
  );
}

const ESTADO_MAIL: Record<string, string> = {
  NO_CONTESTADO: "Sin respuesta",
  CONTESTADO: "Contestó",
  PAGO: "Pagó",
  REBOTADO: "Rebotó",
  SIN_EMAIL: "Sin email",
  FILTRADO: "Filtrado",
};

export default function DashboardPage() {
  const [resumen, setResumen] = useState<DashboardResumen | null>(null);
  const [evolucion, setEvolucion] = useState<EvolucionCiclo[]>([]);
  const [envios, setEnvios] = useState<Envio[]>([]);
  const [morosos, setMorosos] = useState<Moroso[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([getDashboardResumen(), getDashboardEvolucion(), getEnviosActivo(), getMorosos()])
      .then(([r, e, envs, mor]) => {
        setResumen(r);
        setEvolucion(e);
        setEnvios(envs);
        setMorosos(mor);
      })
      .catch((err) => {
        console.error(err);
        setLoadError("No se pudo cargar el dashboard. Probá recargar la página.");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24 w-full" />)}
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const topMonto = [...envios].sort((a, b) => Number(b.monto) - Number(a.monto)).slice(0, 10);

  const chartData = evolucion.map((c) => ({
    label: `#${c.numero} ${format(new Date(c.fecha), "dd/MM", { locale: es })}`,
    valor: Number(c.deuda_total),
  }));

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div className="flex items-baseline gap-3">
        <h1 className="text-xl font-semibold text-foreground">Dashboard</h1>
        <span className="text-sm text-muted-foreground">Estado de la cobranza según el último Excel</span>
      </div>

      {loadError ? (
        <p className="text-sm text-destructive">{loadError}</p>
      ) : !resumen?.hay_ciclo_activo ? (
        <div className="rounded-md border border-dashed border-border py-12 text-center">
          <p className="text-sm font-medium text-foreground">Todavía no hay ciclos cargados</p>
          <p className="text-sm text-muted-foreground">Subí el primer Excel de deudores para empezar a medir.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <KpiCard
              titulo="Deuda actual"
              valor={pesos(resumen.deuda_total)}
              detalle={<VariacionDeuda actual={resumen.deuda_total} anterior={resumen.deuda_total_anterior} />}
            />
            <KpiCard
              titulo="Deudores"
              valor={String(resumen.deudores)}
              detalle={
                resumen.deudores_anterior !== null
                  ? `${resumen.deudores_anterior} en el ciclo anterior`
                  : undefined
              }
            />
            <KpiCard
              titulo="Cobrado desde el ciclo anterior"
              valor={pesos(resumen.cobrado)}
              detalle="Deuda saldada + pagos parciales"
            />
            <KpiCard
              titulo="Deuda +90 días"
              valor={pesos(resumen.deuda_mas_90)}
              detalle="Deuda de más de 90 días — en riesgo"
            />
          </div>

          {chartData.length > 1 && (
            <div className="rounded-md border border-border p-4">
              <p className="mb-3 text-sm font-medium text-foreground">Evolución de la deuda</p>
              <EvolucionChart data={chartData} />
            </div>
          )}

          <Tabs defaultValue="monto">
            <TabsList>
              <TabsTrigger value="monto">Top deudores por monto</TabsTrigger>
              <TabsTrigger value="cronicos">Morosos crónicos</TabsTrigger>
            </TabsList>
            <TabsContent value="monto">
              {topMonto.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No hay deudores en el ciclo activo.
                </p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Consorcio</th>
                      <th className="py-2 pr-4 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">Monto</th>
                      <th className="py-2 pr-4 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">Ciclos debiendo</th>
                      <th className="py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Último mail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topMonto.map((e) => (
                      <tr key={e.id}
                        className="cursor-pointer border-b border-border last:border-0 hover:bg-muted/50"
                        onClick={() => navigate(`/clientes/${encodeURIComponent(e.clave_union)}`)}>
                        <td className="py-2.5 pr-4 text-foreground">{e.nombre_consorcio}</td>
                        <td className="py-2.5 pr-4 text-right tabular-nums">{pesos(Number(e.monto))}</td>
                        <td className="py-2.5 pr-4 text-right tabular-nums">{e.ciclo_numero}</td>
                        <td className="py-2.5 text-muted-foreground">{ESTADO_MAIL[e.estado] ?? e.estado}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </TabsContent>
            <TabsContent value="cronicos">
              {morosos.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No hay deudores con deuda vigente.
                </p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Consorcio</th>
                      <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Debe hace</th>
                      <th className="py-2 pr-4 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">Monto</th>
                      <th className="py-2 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">Recordatorios</th>
                    </tr>
                  </thead>
                  <tbody>
                    {morosos.map((m) => {
                      const dias = differenceInDays(new Date(), new Date(m.deudor_desde));
                      return (
                        <tr key={m.clave_union}
                          className="cursor-pointer border-b border-border last:border-0 hover:bg-muted/50"
                          onClick={() => navigate(`/clientes/${encodeURIComponent(m.clave_union)}`)}>
                          <td className="py-2.5 pr-4 text-foreground">{m.nombre_consorcio}</td>
                          <td className={`py-2.5 pr-4 ${dias > 90 ? "font-medium text-destructive" : "text-muted-foreground"}`}>
                            {formatDistanceToNow(new Date(m.deudor_desde), { locale: es })}
                          </td>
                          <td className="py-2.5 pr-4 text-right tabular-nums">{pesos(Number(m.monto))}</td>
                          <td className="py-2.5 text-right tabular-nums text-muted-foreground">{m.ciclos_debiendo}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
