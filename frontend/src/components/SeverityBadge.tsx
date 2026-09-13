import type { Severity } from "../api";

const STYLES: Record<Severity, { text: string; bg: string; border: string }> = {
  critical: { text: "var(--critical)", bg: "var(--critical-bg)", border: "var(--critical-border)" },
  high: { text: "var(--high)", bg: "var(--high-bg)", border: "var(--high-border)" },
  medium: { text: "var(--medium)", bg: "var(--medium-bg)", border: "var(--medium-border)" },
  low: { text: "var(--low)", bg: "var(--low-bg)", border: "var(--low-border)" },
};

export default function SeverityBadge({ severity }: { severity: Severity }) {
  const style = STYLES[severity] || STYLES.low;
  return (
    <span
      className="mono"
      style={{
        color: style.text,
        background: style.bg,
        border: `1px solid ${style.border}`,
        padding: "3px 10px",
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "0.06em",
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: style.text }} />
      {severity}
    </span>
  );
}
