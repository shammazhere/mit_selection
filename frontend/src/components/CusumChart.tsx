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
import type { CusumPoint, TimelineEvent } from "../api";

interface CusumChartProps {
  path: (number | CusumPoint)[];
  timeline?: TimelineEvent[];
}

interface ChartDataPoint {
  time: string;
  fullTimestamp: string;
  value: number;
  event: string;
}

// Custom dark-mode tooltip showing exact time and trigger event
function CustomCusumTooltip({ active, payload }: any) {
  if (!active || !payload || !payload.length) return null;
  const d: ChartDataPoint = payload[0].payload;
  const isExceeded = d.value >= 0.25;

  return (
    <div
      style={{
        background: "var(--panel)",
        border: `1px solid ${isExceeded ? "var(--critical-border)" : "var(--line)"}`,
        borderRadius: 8,
        padding: "10px 14px",
        boxShadow: "0 8px 24px rgba(0, 0, 0, 0.6)",
        maxWidth: 340,
        color: "var(--ink)",
      }}
    >
      <div className="mono" style={{ fontSize: 11, color: "var(--muted)", marginBottom: 6 }}>
        ⏱️ {d.fullTimestamp || d.time}
      </div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, marginBottom: 6 }}>
        <span style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          CUSUM Drift:
        </span>
        <span className="mono" style={{ fontSize: 16, fontWeight: 700, color: isExceeded ? "var(--critical)" : "var(--high)" }}>
          {d.value.toFixed(3)}
        </span>
      </div>
      <div style={{ marginBottom: d.event ? 8 : 0 }}>
        <span
          className="mono"
          style={{
            display: "inline-block",
            fontSize: 10,
            fontWeight: 600,
            padding: "2px 6px",
            borderRadius: 4,
            background: isExceeded ? "var(--critical-bg)" : "var(--low-bg)",
            color: isExceeded ? "var(--critical)" : "var(--low)",
          }}
        >
          {isExceeded ? "⚠️ THRESHOLD EXCEEDED (≥ 0.25)" : "✓ IN CONTROL (< 0.25)"}
        </span>
      </div>
      {d.event && (
        <div
          style={{
            fontSize: 12,
            color: "var(--ink-secondary)",
            lineHeight: 1.4,
            borderTop: "1px solid var(--line)",
            paddingTop: 6,
            wordBreak: "break-word",
          }}
        >
          <span style={{ color: "var(--muted)", fontSize: 11 }}>Trigger Event: </span>
          {d.event}
        </div>
      )}
    </div>
  );
}

export default function CusumChart({ path, timeline = [] }: CusumChartProps) {
  if (!path || path.length === 0) {
    return (
      <div className="card" style={{ padding: "18px 20px" }}>
        <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>
          Temporal Drift Accumulation (CUSUM Control Chart)
        </h3>
        <p style={{ margin: "8px 0 0 0", fontSize: 13, color: "var(--muted)" }}>
          No CUSUM drift data points recorded yet.
        </p>
      </div>
    );
  }

  // Transform path items into ChartDataPoint with real timestamps
  const data: ChartDataPoint[] = path.map((item, index) => {
    // 1. If item is already a rich object with timestamp/time
    if (typeof item === "object" && item !== null) {
      const val = Number((item.value ?? 0).toFixed(3));
      let displayTime = item.time || "";
      if (!displayTime && item.timestamp) {
        displayTime = item.timestamp.includes("T")
          ? item.timestamp.split("T")[1].slice(0, 8)
          : item.timestamp;
      }
      return {
        time: displayTime || `P${index + 1}`,
        fullTimestamp: item.timestamp || item.time || "",
        value: val,
        event: item.event || item.label || "",
      };
    }

    // 2. If item is a number, correlate dynamically with timeline events
    const val = Number(Number(item).toFixed(3));
    let displayTime = `T+${index * 2}m`;
    let fullTimestamp = "";
    let eventName = "";

    if (index === 0) {
      // First point is the baseline before initial suspicious activity
      if (timeline.length > 0 && timeline[0].timestamp) {
        const rawTime = timeline[0].timestamp.includes("T")
          ? timeline[0].timestamp.split("T")[1].slice(0, 8)
          : timeline[0].timestamp;
        displayTime = `${rawTime} (Base)`;
        fullTimestamp = `${timeline[0].timestamp} (Baseline Started)`;
      } else {
        displayTime = "Baseline";
      }
      eventName = "Session baseline established";
    } else {
      // Points 1..N map to timeline events
      const evtIdx = index - 1;
      if (evtIdx < timeline.length) {
        const evt = timeline[evtIdx];
        fullTimestamp = evt.timestamp;
        displayTime = evt.timestamp.includes("T")
          ? evt.timestamp.split("T")[1].slice(0, 8)
          : evt.timestamp;
        eventName = evt.event;
      } else if (timeline.length > 0) {
        const lastEvt = timeline[timeline.length - 1];
        fullTimestamp = lastEvt.timestamp;
        displayTime = lastEvt.timestamp.includes("T")
          ? lastEvt.timestamp.split("T")[1].slice(0, 8)
          : lastEvt.timestamp;
        eventName = lastEvt.event;
      }
    }

    return {
      time: displayTime,
      fullTimestamp,
      value: val,
      event: eventName,
    };
  });

  const values = data.map((d) => d.value);
  const latestVal = values[values.length - 1] ?? 0;
  const maxVal = Math.max(0.5, ...values);
  const isDriftExceeded = latestVal >= 0.25;

  return (
    <div className="card" style={{ padding: "18px 20px" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 14,
          flexWrap: "wrap",
          gap: 10,
        }}
      >
        <div>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>
            Temporal Drift Accumulation (CUSUM Control Chart)
          </h3>
          <p style={{ margin: "4px 0 0 0", fontSize: 12, color: "var(--muted)" }}>
            Monitors sustained upward shift in pre-multiplier fused score. Points record exact event timestamps. Dashed red line represents the 0.25 drift threshold.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span
            className="mono"
            style={{
              fontSize: 11,
              fontWeight: 600,
              padding: "3px 8px",
              borderRadius: 4,
              background: isDriftExceeded ? "var(--critical-bg)" : "var(--low-bg)",
              color: isDriftExceeded ? "var(--critical)" : "var(--low)",
              border: `1px solid ${isDriftExceeded ? "var(--critical-border)" : "var(--low-border)"}`,
            }}
          >
            {isDriftExceeded ? "DRIFT DETECTED (≥ 0.25)" : "STABLE / IN CONTROL"}
          </span>
          <div
            className="mono"
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: isDriftExceeded ? "var(--critical)" : "var(--cyan)",
              background: "var(--bg-subtle)",
              border: "1px solid var(--line)",
              padding: "3px 8px",
              borderRadius: 4,
            }}
          >
            Latest: {latestVal.toFixed(3)}
          </div>
        </div>
      </div>

      <div style={{ height: 260, width: "100%" }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="cusumGradient" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="5%"
                  stopColor={isDriftExceeded ? "var(--critical)" : "var(--high)"}
                  stopOpacity={0.4}
                />
                <stop
                  offset="95%"
                  stopColor={isDriftExceeded ? "var(--critical)" : "var(--high)"}
                  stopOpacity={0.0}
                />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
            <XAxis
              dataKey="time"
              stroke="var(--muted)"
              fontSize={11}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <YAxis
              stroke="var(--muted)"
              fontSize={11}
              tickLine={false}
              domain={[0, Math.max(0.5, Math.ceil(maxVal * 1.2 * 10) / 10)]}
            />
            <Tooltip content={<CustomCusumTooltip />} />
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
              stroke={isDriftExceeded ? "var(--critical)" : "var(--high)"}
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

