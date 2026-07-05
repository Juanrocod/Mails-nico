import { CheckCircle2, AlertTriangle } from "lucide-react";

interface ProgresoEnvioProps {
  enviado: number;
  total: number;
}

export function EnvioCompletado({ enviados, total }: { enviados: number; total: number }) {
  if (enviados >= total) {
    return (
      <div className="flex items-center gap-2 rounded-md bg-success px-3 py-2 text-sm text-success-foreground">
        <CheckCircle2 className="h-4 w-4 shrink-0" />
        <span>
          Envío completado — {total} mail{total === 1 ? "" : "s"} enviado{total === 1 ? "" : "s"} correctamente.
        </span>
      </div>
    );
  }

  const fallidos = total - enviados;
  return (
    <div className="flex items-center gap-2 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning-text">
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <span>
        Se enviaron {enviados} de {total} mails. {fallidos} no se pudo{fallidos === 1 ? "" : "n"} mandar — buscalo
        {fallidos === 1 ? "" : "s"} en "Para enviar" para reintentar.
      </span>
    </div>
  );
}

export function ProgresoEnvio({ enviado, total }: ProgresoEnvioProps) {
  const pct = total > 0 ? Math.round((enviado / total) * 100) : 0;
  return (
    <div className="w-full space-y-2">
      <div className="flex justify-between text-sm text-foreground">
        <span className="font-medium">Enviando mails...</span>
        <span className="tabular-nums text-muted-foreground">
          {enviado} / {total}
        </span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        className="w-full bg-border rounded-full h-2.5 overflow-hidden"
      >
        <div
          className="bg-primary h-full rounded-full transition-[width] duration-300 ease-out motion-reduce:transition-none"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs tabular-nums text-muted-foreground text-right">{pct}% completado</p>
    </div>
  );
}
