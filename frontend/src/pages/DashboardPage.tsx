import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Skeleton } from "../components/ui/skeleton";
import { getDashboardResumen, getDashboardEvolucion } from "../services/dashboard";
import { getEnviosActivo } from "../services/ciclos";
import type { DashboardResumen, EvolucionCiclo, Envio } from "../types/domain";

function pesos(n: number | null): string {
  if (n === null) return "—";
  return `$${Number(n).toLocaleString("es-AR")}`;
}

function variacion(actual: number, anterior: number | null): string {
  if (anterior === null || anterior === 0) return "";
  const pct = ((actual - anterior) / anterior) * 100;
  const signo = pct > 0 ? "+" : "";
  return `${signo}${pct.toFixed(1)}% vs. ciclo anterior`;
}

function KpiCard({ titulo, valor, detalle }: { titulo: string; valor: string; detalle?: string }) {
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
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([getDashboardResumen(), getDashboardEvolucion(), getEnviosActivo()])
      .then(([r, e, envs]) => {
        setResumen(r);
        setEvolucion(e);
        setEnvios(envs);
      })
      .catch(console.error)
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
  const topCronicos = [...envios]
    .filter((e) => e.ciclo_numero > 1)
    .sort((a, b) => b.ciclo_numero - a.ciclo_numero || Number(b.monto) - Number(a.monto))
    .slice(0, 10);

  const chartData = evolucion.map((c) => ({
    nombre: `#${c.numero} ${format(new Date(c.fecha), "dd/MM", { locale: es })}`,
    deuda: Number(c.deuda_total),
    cobrado: c.cobrado === null ? 0 : Number(c.cobrado),
    deudores: c.deudores,
  }));

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div className="flex items-baseline gap-3">
        <h1 className="text-xl font-semibold text-foreground">Dashboard</h1>
        <span className="text-sm text-muted-foreground">Estado de la cobranza según el último Excel</span>
      </div>

      {!resumen?.hay_ciclo_activo ? (
        <div className="rounded-md border border-dashed border-border py-12 text-center">
          <p className="text-sm font-medium text-foreground">Todavía no hay ciclos cargados</p>
          <p className="text-sm text-muted-foreground">Subí el primer Excel de deudores para empezar a medir.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <KpiCard
              titulo="Deuda total"
              valor={pesos(resumen.deuda_total)}
              detalle={variacion(resumen.deuda_total, resumen.deuda_total_anterior)}
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
              titulo="Saldaron tras el recordatorio"
              valor={resumen.efectividad === null ? "—" : `${resumen.efectividad}%`}
              detalle="De los que recibieron mail el ciclo pasado"
            />
          </div>

          {chartData.length > 1 && (
            <div className="rounded-md border border-border p-4">
              <p className="mb-3 text-sm font-medium text-foreground">Evolución por ciclo</p>
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="nombre" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(value: unknown, name: unknown) =>
                    name === "Deudores" ? (value as number) : `$${Number(value).toLocaleString("es-AR")}`
                  } />
                  <Legend />
                  <Bar dataKey="cobrado" name="Cobrado" fill="hsl(var(--primary))" opacity={0.5} />
                  <Line type="monotone" dataKey="deuda" name="Deuda total" stroke="hsl(var(--primary))" strokeWidth={2} dot />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

          <Tabs defaultValue="monto">
            <TabsList>
              <TabsTrigger value="monto">Top deudores por monto</TabsTrigger>
              <TabsTrigger value="cronicos">Morosos crónicos</TabsTrigger>
            </TabsList>
            {(["monto", "cronicos"] as const).map((tab) => {
              const list = tab === "monto" ? topMonto : topCronicos;
              return (
                <TabsContent key={tab} value={tab}>
                  {list.length === 0 ? (
                    <p className="py-8 text-center text-sm text-muted-foreground">
                      {tab === "cronicos"
                        ? "Nadie lleva más de un ciclo debiendo."
                        : "No hay deudores en el ciclo activo."}
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
                        {list.map((e) => (
                          <tr
                            key={e.id}
                            className="cursor-pointer border-b border-border last:border-0 hover:bg-muted/50"
                            onClick={() => navigate(`/clientes/${encodeURIComponent(e.clave_union)}`)}
                          >
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
              );
            })}
          </Tabs>
        </>
      )}
    </div>
  );
}
