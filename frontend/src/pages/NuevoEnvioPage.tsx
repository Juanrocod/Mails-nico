import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Send, MailX, Filter } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { ProgresoEnvio } from "../components/upload/ProgresoEnvio";
import { useCicloContext } from "../contexts/useCicloContext";
import type { MotivoFiltrado } from "../types/domain";
import { cn } from "../lib/utils";
import { MOTIVO_LABEL, MOTIVO_DOT } from "../lib/estado";

const PATH_TO_TAB: Record<string, string> = {
  "/nuevo-envio/para-enviar": "para_enviar",
  "/nuevo-envio/sin-email": "sin_email",
  "/nuevo-envio/filtrados": "filtrados",
};

interface TableRow {
  key: string;
  nombre_consorcio: string;
  email: string | null;
  monto: number;
  motivo_filtrado: MotivoFiltrado | null;
}

export default function NuevoEnvioPage() {
  const {
    enviosActivo,
    previewData,
    clearPreview,
    confirmarPreview,
    isLoading,
    progreso,
    loadEnviosActivo,
  } = useCicloContext();
  const [initialLoading, setInitialLoading] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();

  const activeTab = PATH_TO_TAB[location.pathname] ?? "para_enviar";
  const revisando = !!previewData && !isLoading;

  useEffect(() => {
    loadEnviosActivo().finally(() => setInitialLoading(false));
  }, [loadEnviosActivo]);

  const paraEnviar: TableRow[] = revisando
    ? previewData!.items_para_enviar.map((i) => ({ key: i.clave_union, ...i }))
    : enviosActivo
        .filter((e) => e.estado === "NO_CONTESTADO" && e.email)
        .map((e) => ({ key: e.id, ...e }));
  const sinEmail: TableRow[] = revisando
    ? previewData!.items_sin_email.map((i) => ({ key: i.clave_union, ...i }))
    : enviosActivo.filter((e) => e.estado === "SIN_EMAIL").map((e) => ({ key: e.id, ...e }));
  const filtrados: TableRow[] = revisando
    ? previewData!.items_filtrados.map((i) => ({ key: i.clave_union, ...i }))
    : enviosActivo.filter((e) => e.estado === "FILTRADO").map((e) => ({ key: e.id, ...e }));

  function handleTabChange(value: string) {
    const paths: Record<string, string> = {
      para_enviar: "/nuevo-envio/para-enviar",
      sin_email: "/nuevo-envio/sin-email",
      filtrados: "/nuevo-envio/filtrados",
    };
    navigate(paths[value] ?? "/nuevo-envio/para-enviar");
  }

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div className="flex items-baseline gap-3">
        <h1 className="text-xl font-semibold text-foreground">Nuevo Envío</h1>
        <span className="text-sm text-muted-foreground">
          {revisando
            ? "Revisá el ciclo antes de confirmar el envío"
            : "Ciclo actual antes de confirmar el envío de mails"}
        </span>
      </div>

      {revisando && (
        <div className="flex items-center justify-between gap-4 rounded-md border border-border bg-secondary/40 p-3">
          <p className="text-sm text-muted-foreground">
            Sin confirmar todavía — revisá las 3 solapas y confirmá cuando esté todo bien.
          </p>
          <div className="flex gap-2 shrink-0">
            <Button variant="outline" size="sm" onClick={clearPreview}>
              Cancelar
            </Button>
            <Button size="sm" onClick={() => confirmarPreview()}>
              Enviar {previewData!.para_enviar} mails
            </Button>
          </div>
        </div>
      )}

      {progreso && isLoading && (
        <div className="rounded-md border border-border bg-secondary/60 p-4">
          <ProgresoEnvio enviado={progreso.enviado} total={progreso.total} />
        </div>
      )}

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="para_enviar" className="gap-1.5">
            <Send className="h-3.5 w-3.5" />
            Para enviar
            {paraEnviar.length > 0 && (
              <Badge variant="secondary" className="text-xs tabular-nums">
                {paraEnviar.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="sin_email" className="gap-1.5">
            <MailX className="h-3.5 w-3.5" />
            Sin Email
            {sinEmail.length > 0 && (
              <Badge variant="secondary" className="text-xs tabular-nums">
                {sinEmail.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="filtrados" className="gap-1.5">
            <Filter className="h-3.5 w-3.5" />
            Filtrados
            {filtrados.length > 0 && (
              <Badge variant="secondary" className="text-xs tabular-nums">
                {filtrados.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="para_enviar">
          <EnvioTable
            envios={paraEnviar}
            loading={!revisando && initialLoading}
            emptyState={
              <EmptyState
                title="No hay deudores para enviar"
                description="Subí el Excel de deudores para armar el próximo ciclo de envío."
              />
            }
          />
        </TabsContent>
        <TabsContent value="sin_email">
          <EnvioTable
            envios={sinEmail}
            loading={!revisando && initialLoading}
            emptyState={
              <EmptyState
                title="Todos los deudores tienen email"
                description="Ninguno quedó sin match en el maestro de clientes."
              />
            }
          />
        </TabsContent>
        <TabsContent value="filtrados">
          <EnvioTable
            envios={filtrados}
            loading={!revisando && initialLoading}
            emptyState={
              <EmptyState
                title="No hay deudores filtrados"
                description="Nadie quedó afuera por monto mínimo o baja voluntaria en este ciclo."
              />
            }
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 rounded-md border border-dashed border-border py-12 text-center">
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="text-sm text-muted-foreground max-w-sm">{description}</p>
    </div>
  );
}

function EnvioTable({
  envios,
  loading,
  emptyState,
}: {
  envios: TableRow[];
  loading?: boolean;
  emptyState: React.ReactNode;
}) {
  if (loading) {
    return (
      <div className="space-y-2 pt-2">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-9 w-full" />
        ))}
      </div>
    );
  }

  if (envios.length === 0) {
    return <div className="pt-2">{emptyState}</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm table-fixed">
        <colgroup>
          <col className="w-[35%]" />
          <col className="w-[30%]" />
          <col className="w-[20%]" />
          <col className="w-[15%]" />
        </colgroup>
        <thead>
          <tr className="border-b border-border text-left">
            <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Consorcio
            </th>
            <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Email
            </th>
            <th className="py-2 pr-4 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Monto
            </th>
            <th className="py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Motivo
            </th>
          </tr>
        </thead>
        <tbody>
          {envios.map((e) => (
            <tr key={e.key} className="border-b border-border last:border-0 hover:bg-muted/50">
              <td className="py-2.5 pr-4 text-foreground truncate">{e.nombre_consorcio}</td>
              <td className="py-2.5 pr-4 text-muted-foreground truncate">{e.email ?? "—"}</td>
              <td className="py-2.5 pr-4 text-right tabular-nums text-foreground">
                ${Number(e.monto).toLocaleString("es-AR")}
              </td>
              <td className="py-2.5">
                {e.motivo_filtrado ? (
                  <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                    <span
                      className={cn("h-1.5 w-1.5 rounded-full shrink-0", MOTIVO_DOT[e.motivo_filtrado])}
                      aria-hidden
                    />
                    {MOTIVO_LABEL[e.motivo_filtrado]}
                  </span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
