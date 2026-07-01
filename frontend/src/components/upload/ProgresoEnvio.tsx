interface ProgresoEnvioProps {
  enviado: number;
  total: number;
}

export function ProgresoEnvio({ enviado, total }: ProgresoEnvioProps) {
  const pct = total > 0 ? Math.round((enviado / total) * 100) : 0;
  return (
    <div className="w-full space-y-2">
      <div className="flex justify-between text-sm text-gray-600">
        <span>Enviando mails...</span>
        <span>{enviado} / {total}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3">
        <div
          className="bg-blue-600 h-3 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-gray-500 text-right">{pct}% completado</p>
    </div>
  );
}
