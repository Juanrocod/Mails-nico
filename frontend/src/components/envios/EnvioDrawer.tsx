import { Sheet, SheetContent, SheetHeader, SheetTitle } from "../ui/sheet";
import { Button } from "../ui/button";
import type { Envio } from "../../types/domain";

interface Props {
  envio: Envio | null;
  onClose: () => void;
  onMarcarPago: (id: string) => void;
}

export function EnvioDrawer({ envio, onClose, onMarcarPago }: Props) {
  return (
    <Sheet open={!!envio} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent>
        {envio && (
          <>
            <SheetHeader>
              <SheetTitle>{envio.nombre_consorcio}</SheetTitle>
            </SheetHeader>
            <div className="mt-4 space-y-3 text-sm">
              <Row label="Email" value={envio.email ?? "—"} />
              <Row label="Monto" value={`$${Number(envio.monto).toLocaleString("es-AR")}`} />
              <Row label="Estado" value={envio.estado.replace("_", " ")} />
              <Row label="Ciclo #" value={String(envio.ciclo_numero)} />
              {envio.enviado_en && (
                <Row
                  label="Enviado"
                  value={new Date(envio.enviado_en).toLocaleString("es-AR")}
                />
              )}
              {envio.reply_snippet && (
                <div>
                  <p className="text-gray-500 mb-1">Respuesta:</p>
                  <p className="bg-gray-50 rounded p-2 text-xs whitespace-pre-wrap">
                    {envio.reply_snippet}
                  </p>
                </div>
              )}
              {envio.estado === "CONTESTADO" && (
                <Button
                  className="w-full mt-4"
                  onClick={() => {
                    onMarcarPago(envio.id);
                    onClose();
                  }}
                >
                  Marcar como PAGO
                </Button>
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
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
