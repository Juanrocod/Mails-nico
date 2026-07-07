import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import type { TooltipContentProps } from "recharts";

function ChartTooltip({ active, payload, label }: TooltipContentProps) {
  if (!active || !payload || payload.length === 0) return null;
  const valor = payload[0].value ?? 0;
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-foreground">{label}</p>
      <p className="tabular-nums text-muted-foreground">
        ${Number(valor).toLocaleString("es-AR")}
      </p>
    </div>
  );
}

export function EvolucionChart({ data }: { data: { label: string; valor: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="evoGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="oklch(var(--primary))" stopOpacity={0.35} />
            <stop offset="100%" stopColor="oklch(var(--primary))" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="oklch(var(--border))" strokeOpacity={0.4} />
        <XAxis
          dataKey="label"
          tick={{ fill: "oklch(var(--muted-foreground))", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "oklch(var(--muted-foreground))", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={48}
          tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
        />
        <Tooltip content={(props) => <ChartTooltip {...props} />} cursor={{ stroke: "oklch(var(--border))" }} />
        <Area
          type="monotone"
          dataKey="valor"
          stroke="oklch(var(--primary))"
          strokeWidth={2}
          fill="url(#evoGrad)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
