import type React from "react";
import type { Envio } from "../../types/domain";
import { cn } from "../../lib/utils";
import { Badge } from "../ui/badge";
import { Card } from "../ui/card";
import { ESTADO_BADGE, ESTADO_LABEL } from "../../lib/estado";

interface Props {
  envio: Envio;
  onClick: () => void;
}

export function EnvioCard({ envio, onClick }: Props) {
  return (
    <Card
      role="button"
      tabIndex={0}
      onKeyDown={(e: React.KeyboardEvent) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      className="p-4 cursor-pointer hover:shadow-md transition-all select-none"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0 space-y-1.5">
          <span className="font-medium text-sm text-foreground truncate block">
            {envio.nombre_consorcio}
          </span>
          <p className="text-sm text-muted-foreground">
            ${Number(envio.monto).toLocaleString("es-AR")}
          </p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
            <span>{envio.email ?? "Sin email"}</span>
            {envio.reply_snippet && (
              <>
                <span>·</span>
                <span className="truncate">{envio.reply_snippet}</span>
              </>
            )}
          </div>
        </div>

        <Badge
          variant="outline"
          className={cn("text-xs shrink-0 self-start border-transparent", ESTADO_BADGE[envio.estado])}
        >
          {ESTADO_LABEL[envio.estado]}
        </Badge>
      </div>
    </Card>
  );
}
