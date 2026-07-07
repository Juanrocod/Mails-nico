import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { format, formatDistanceToNow, differenceInDays } from "date-fns";
import { es } from "date-fns/locale";
import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { getHistorialCliente } from "../services/maestro";
import { getCiclos } from "../services/ciclos";
import type { HistorialCliente, CicloResumen } from "../types/domain";
import { EvolucionChart } from "../components/dashboard/EvolucionChart";
import { categoriaRiesgo } from "../lib/estado";

const ESTADO_LABEL: Record<string, string> = {
  NO_CONTESTADO: "Sin respuesta",
  CONTESTADO: "Contestó",
  PAGO: "Pagó",
  REBOTADO: "Rebotó",
  SIN_EMAIL: "Sin email",
  FILTRADO: "Filtrado",
};

function pesos(n: number): string {
  return `$${Number(n).toLocaleString("es-AR")}`;
}

export default function ClientePerfilPage() {
  const { clave } = useParams<{ clave: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<HistorialCliente | null>(null);
  const [ciclos, setCiclos] = useState<CicloResumen[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!clave) return;
    Promise.all([getHistorialCliente(clave), getCiclos()])
      .then(([d, cs]) => {
        setData(d);
        setCiclos(cs);
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Error cargando el perfil"))
      .finally(() => setLoading(false));
  }, [clave]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto space-y-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="mr-1.5 h-3.5 w-3.5" /> Volver
        </Button>
        <p className="text-sm text-destructive">{error || "No se encontró el cliente."}</p>
      </div>
    );
  }

  const items = data.items;
  const desde = data.deudor_desde ? new Date(data.deudor_desde) : null;
  const diasDebiendo = desde ? differenceInDays(new Date(), desde) : null;
  // Deuda historica real: desde el primer ciclo en que aparecio hasta hoy, con
  // su deuda en cada ciclo y $0 en los periodos que estuvo al dia (para que se
  // vean los altibajos reales, no una linea continua ficticia).
  const montoPorCiclo = new Map(items.map((i) => [i.ciclo, Number(i.monto)]));
  const primerCiclo = items.length ? Math.min(...items.map((i) => i.ciclo)) : 0;
  const serieDeuda = [...ciclos]
    .filter((c) => c.numero >= primerCiclo)
    .sort((a, b) => a.numero - b.numero)
    .map((c) => {
      const m = format(new Date(c.creado_en), "MMM yy", { locale: es });
      return { label: m.charAt(0).toUpperCase() + m.slice(1), valor: montoPorCiclo.get(c.numero) ?? 0 };
    });
  const actual = items.find((i) => i.ciclo_activo);
  // Racha vigente: desde el mas reciente hacia atras hasta un ciclo saldado/pagado.
  // Mismo criterio que deudor_desde del backend, para contar mails de ESTA deuda.
  const rachaItems: typeof items = [];
  for (const it of items) {
    if (it.saldado_en || it.estado === "PAGO") break;
    rachaItems.push(it);
  }
  const recordatoriosDeuda = rachaItems.filter((i) => i.recibio_mail).length;
  const respuestasDeuda = rachaItems.filter((i) => i.reply_en).length;
  const totalSaldado = items.filter((i) => i.saldado_en).reduce((acc, i) => acc + Number(i.monto), 0);
  const conMail = items.filter((i) => i.recibio_mail);
  const contesto = conMail.filter((i) => i.reply_en).length;
  const estadoCliente = !data.cliente
    ? "No está en el Maestro"
    : data.cliente.prefiere_no_recibir_email
      ? "Dado de baja"
      : data.cliente.activo
        ? "Activo"
        : "Eliminado";

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
        <ArrowLeft className="mr-1.5 h-3.5 w-3.5" /> Volver
      </Button>

      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold text-foreground">
            {data.cliente?.nombre ?? `Clave ${data.clave_union}`}
          </h1>
          <span className="font-mono text-xs text-muted-foreground">{data.clave_union}</span>
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${categoriaRiesgo(data.deudor_desde).badge}`}>
            {categoriaRiesgo(data.deudor_desde).label}
          </span>
        </div>
        <p className="mt-0.5 text-sm text-muted-foreground">
          {data.cliente?.email ?? "Sin email"} · {data.cliente?.localidad ?? "Sin localidad"} · {estadoCliente}
          {desde && (
            <>
              {" · "}
              <span className={diasDebiendo !== null && diasDebiendo > 90 ? "font-medium text-destructive" : ""}>
                Deudor desde {format(desde, "dd/MM/yyyy", { locale: es })} (hace {formatDistanceToNow(desde, { locale: es })})
              </span>
            </>
          )}
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="rounded-md border border-border bg-secondary/30 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Deuda actual</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{actual ? pesos(Number(actual.monto)) : "—"}</p>
        </div>
        <div className="rounded-md border border-border bg-secondary/30 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Debe hace</p>
          <p className={`mt-1 text-2xl font-semibold tabular-nums ${diasDebiendo !== null && diasDebiendo > 90 ? "text-destructive" : ""}`}>
            {desde ? formatDistanceToNow(desde, { locale: es }) : "—"}
          </p>
          {desde && (
            <p className="mt-0.5 text-xs text-muted-foreground">
              {recordatoriosDeuda} recordatorio{recordatoriosDeuda === 1 ? "" : "s"} sobre esta deuda · {respuestasDeuda} respuesta{respuestasDeuda === 1 ? "" : "s"}
            </p>
          )}
        </div>
        <div className="rounded-md border border-border bg-secondary/30 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Saldado histórico</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{pesos(totalSaldado)}</p>
        </div>
        <div className="rounded-md border border-border bg-secondary/30 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Respuesta a mails</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">
            {conMail.length === 0 ? "—" : `${contesto} de ${conMail.length}`}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">histórico del cliente</p>
        </div>
      </div>

      {serieDeuda.length > 1 && (
        <div className="rounded-md border border-border p-4">
          <p className="mb-3 text-sm font-medium text-foreground">Evolución de su deuda</p>
          <EvolucionChart data={serieDeuda} />
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left">
              <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Ciclo</th>
              <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Fecha</th>
              <th className="py-2 pr-4 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">Monto</th>
              <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Mail</th>
              <th className="py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Resultado</th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.envio_id} className="border-b border-border last:border-0">
                <td className="py-2.5 pr-4 tabular-nums">#{i.ciclo}{i.ciclo_activo ? " (actual)" : ""}</td>
                <td className="py-2.5 pr-4 text-muted-foreground">
                  {format(new Date(i.fecha), "dd/MM/yyyy", { locale: es })}
                </td>
                <td className="py-2.5 pr-4 text-right tabular-nums">{pesos(Number(i.monto))}</td>
                <td className="py-2.5 pr-4 text-muted-foreground">
                  {i.recibio_mail ? ESTADO_LABEL[i.estado] ?? i.estado : "No se envió"}
                </td>
                <td className="py-2.5">
                  {i.saldado_en
                    ? `Saldado el ${format(new Date(i.saldado_en), "dd/MM/yyyy", { locale: es })}`
                    : i.ciclo_activo
                      ? "Deuda vigente"
                      : "Siguió debiendo"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
