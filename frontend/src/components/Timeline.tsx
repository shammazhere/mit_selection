import type { TimelineEvent } from "../api";

function getEventBadge(text: string): { label: string; color: string; bg: string } {
  const t = text.toLowerCase();
  if (t.includes("usb") || t.includes("removable media") || t.includes("connect")) {
    return { label: "DEVICE/USB", color: "var(--high)", bg: "var(--high-bg)" };
  }
  if (t.includes("upload") || t.includes("dropbox") || t.includes("wetransfer")) {
    return { label: "EXFILTRATION", color: "var(--critical)", bg: "var(--critical-bg)" };
  }
  if (t.includes("file copy") || t.includes("copied file")) {
    return { label: "FILE COPY", color: "var(--high)", bg: "var(--high-bg)" };
  }
  if (t.includes("email")) {
    return { label: "EXTERNAL COMM", color: "var(--cyan)", bg: "rgba(72, 202, 228, 0.12)" };
  }
  if (t.includes("logon") || t.includes("after-hours")) {
    return { label: "AFTER-HOURS AUTH", color: "#e0a54b", bg: "rgba(224, 165, 75, 0.12)" };
  }
  if (t.includes("fallback")) {
    return { label: "COHORT FALLBACK", color: "var(--cyan)", bg: "rgba(72, 202, 228, 0.15)" };
  }
  if (t.includes("calibration") || t.includes("false-positive") || t.includes("down-weight") || t.includes("investigator resolution") || t.includes("overridden")) {
    return { label: "INVESTIGATOR RESOLUTION", color: "var(--low)", bg: "var(--low-bg)" };
  }
  return { label: "ANOMALY SIGNAL", color: "var(--medium)", bg: "var(--medium-bg)" };
}

export default function Timeline({ events }: { events: TimelineEvent[] }) {
  if (!events.length) {
    return <p style={{ color: "var(--muted)", margin: 0 }}>No forensic events recorded on this case.</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, width: "100%", maxWidth: "100%" }}>
      {events.map((item, idx) => {
        const badge = getEventBadge(item.event);
        return (
          <div
            key={`${item.timestamp}-${idx}`}
            style={{
              display: "flex",
              gap: 14,
              padding: "12px 16px",
              background: "var(--bg-subtle)",
              border: "1px solid var(--line)",
              borderRadius: "var(--radius-sm)",
              alignItems: "flex-start",
              transition: "border-color 0.2s ease",
              width: "100%",
              maxWidth: "100%",
              boxSizing: "border-box",
              overflow: "hidden",
            }}
          >
            <div style={{ minWidth: 140, flexShrink: 0 }}>
              <div className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>
                {item.timestamp.replace("T", " ")}
              </div>
              <span
                className="mono"
                style={{
                  display: "inline-block",
                  marginTop: 4,
                  fontSize: 10,
                  fontWeight: 600,
                  padding: "2px 6px",
                  borderRadius: 4,
                  color: badge.color,
                  background: badge.bg,
                }}
              >
                {badge.label}
              </span>
            </div>

            <div
              style={{
                flex: 1,
                minWidth: 0,
                fontSize: 13,
                lineHeight: 1.5,
                color: "var(--ink-secondary)",
                wordBreak: "break-word",
                overflowWrap: "anywhere",
                whiteSpace: "normal",
              }}
            >
              {item.event}
            </div>
          </div>
        );
      })}
    </div>
  );
}
