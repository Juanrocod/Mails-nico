import type { Envio } from "../../types/domain";

const ESTADO_BADGE: Record<string, string> = {
  NO_CONTESTADO: "bg-yellow-100 text-yellow-800",
  CONTESTADO: "bg-blue-100 text-blue-800",
  PAGO: "bg-green-100 text-green-800",
  REBOTADO: "bg-red-100 text-red-800",
};

interface Props {
  envio: Envio;
  onClick: () => void;
}

export function EnvioCard({ envio, onClick }: Props) {
  return (
    <div
      className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-medium">{envio.nombre_consorcio}</p>
          <p className="text-sm text-gray-500">{envio.email ?? "Sin email"}</p>
        </div>
        <div className="text-right">
          <p className="font-semibold">${Number(envio.monto).toLocaleString("es-AR")}</p>
          <span className={`text-xs px-2 py-0.5 rounded-full ${ESTADO_BADGE[envio.estado] ?? ""}`}>
            {envio.estado.replace("_", " ")}
          </span>
        </div>
      </div>
      {envio.reply_snippet && (
        <p className="text-xs text-gray-400 mt-2 line-clamp-1">{envio.reply_snippet}</p>
      )}
    </div>
  );
}
