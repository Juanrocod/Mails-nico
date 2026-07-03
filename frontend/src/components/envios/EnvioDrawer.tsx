import { Sheet, SheetContent, SheetHeader, SheetTitle } from "../ui/sheet";
import { Separator } from "../ui/separator";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import type { Envio } from "../../types/domain";
import { cn } from "../../lib/utils";
import { ESTADO_BADGE, ESTADO_LABEL } from "../../lib/estado";

interface Props {
  envio: Envio | null;
  onClose: () => void;
  onMarcarPago: (id: string) => void;
}

export function EnvioDrawer({ envio, onClose, onMarcarPago }: Props) {
  return (
    <Sheet open={!!envio} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent
        side="right"
        className="w-[600px] sm:max-w-[600px] p-0 flex flex-col overflow-hidden"
      >
        {envio && (
          <>
            <SheetHeader className="px-6 py-4 border-b border-border shrink-0">
              <div className="flex items-start justify-between gap-3 pr-6">
                <div className="min-w-0">
                  <SheetTitle className="text-base font-semibold truncate">
                    {envio.nombre_consorcio}
                  </SheetTitle>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {envio.clave_union} · Ciclo #{envio.ciclo_numero}
                  </p>
                </div>
                <Badge
                  variant="outline"
                  className={cn("shrink-0 text-xs border-transparent", ESTADO_BADGE[envio.estado])}
                >
                  {ESTADO_LABEL[envio.estado]}
                </Badge>
              </div>
            </SheetHeader>

            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              <section className="space-y-1">
                <Row label="Email" value={envio.email ?? "—"} />
                <Row label="Monto" value={`$${Number(envio.monto).toLocaleString("es-AR")}`} />
                {envio.enviado_en && (
                  <Row label="Enviado" value={new Date(envio.enviado_en).toLocaleString("es-AR")} />
                )}
                {envio.reply_en && (
                  <Row label="Respondido" value={new Date(envio.reply_en).toLocaleString("es-AR")} />
                )}
              </section>

              {envio.reply_snippet && (
                <>
                  <Separator />
                  <section className="space-y-2">
                    <h3 className="text-sm font-medium text-foreground">Respuesta</h3>
                    <div className="max-h-64 overflow-y-auto rounded-md border border-border bg-muted/40 p-3">
                      <p className="text-sm whitespace-pre-wrap text-foreground">
                        {envio.reply_snippet}
                      </p>
                    </div>
                  </section>
                </>
              )}

              {envio.estado === "CONTESTADO" && (
                <>
                  <Separator />
                  <section className="space-y-3">
                    <h3 className="text-sm font-medium text-foreground">Acciones</h3>
                    <Button
                      size="sm"
                      onClick={() => {
                        onMarcarPago(envio.id);
                        onClose();
                      }}
                    >
                      Marcar como pago
                    </Button>
                  </section>
                </>
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 py-1 text-sm">
      <span className="text-muted-foreground shrink-0">{label}</span>
      <span className="text-foreground text-right">{value}</span>
    </div>
  );
}
