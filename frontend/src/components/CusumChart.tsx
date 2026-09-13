import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function CusumChart({ path }: { path: number[] }) {
  const data = path.map((value, index) => ({
    day: `Day ${index + 1}`,
    value: Number(value.toFixed(4)),
  }));

  const maxVal = Math.max(0.5, ...path);

  return (
    <div className="card" style={{ padding: "18px 20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12, flexWrap: "wrap", gap: 8 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>
            Temporal Drift Accumulation (CUSUM Control Chart)
          </h3>
          <p style={{ margin: "4px 0 0 0", fontSize: 12, color: "var(--muted)" }}>
            Monitors sustained upward shifts in the pre-multiplier fused score. Dashed red line represents the 0.25 drift threshold.
          </p>
        </div>
        <div className="mono" style={{ fontSize: 12, color: "var(--cyan)" }}>
          Latest: {path.length ? path[path.length - 1].toFixed(3) : 0}
        </div>
      </div>

      <div style={{ height: 260, width: "100%" }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="cusumGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--high)" stopOpacity={0.4} />
                <stop offset="95%" stopColor="var(--high)" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
            <XAxis dataKey="day" stroke="var(--muted)" fontSize={11} tickLine={false} />
            <YAxis stroke="var(--muted)" fontSize={11} tickLine={false} domain={[0, Math.ceil(maxVal * 1.2 * 10) / 10]} />
            <Tooltip
              contentStyle={{
                background: "var(--bg-subtle)",
                border: "1px solid var(--line)",
                borderRadius: 6,
                color: "var(--ink)",
                fontSize: 12,
                fontFamily: "IBM Plex Mono",
              }}
            />
            <ReferenceLine
              y={0.25}
              stroke="var(--critical)"
              strokeDasharray="4 4"
              label={{
                value: "Drift Threshold (0.25)",
                position: "insideTopRight",
                fill: "var(--critical)",
                fontSize: 10,
                fontFamily: "IBM Plex Mono",
              }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke="var(--high)"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#cusumGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
