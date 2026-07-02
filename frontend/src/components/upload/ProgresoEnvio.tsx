interface ProgresoEnvioProps {
  enviado: number;
  total: number;
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
