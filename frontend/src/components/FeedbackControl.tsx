import { FormEvent, useState } from "react";
import { postFeedback } from "../api";

const PRESETS = [
  "Expected activity: legitimate new project assignment",
  "Approved operational activity: off-hours IT maintenance",
  "Authorized export: scheduled financial audit backup",
  "Role transition in progress (updating cohort context)",
];

export default function FeedbackControl({
  userId,
  isFalsePositive,
  existingReason,
  onFeedbackSubmitted,
}: {
  userId: string;
  isFalsePositive?: boolean;
  existingReason?: string;
  onFeedbackSubmitted?: () => void;
}) {
  const [reason, setReason] = useState(
    existingReason || "Expected activity: legitimate new project assignment"
  );
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [statusMsg, setStatusMsg] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!reason.trim()) return;
    setStatus("loading");
    try {
      await postFeedback(userId, reason);
      setStatus("success");
      setStatusMsg("Marked as false positive. Case down-weighted across fusion signals.");
      if (onFeedbackSubmitted) {
        onFeedbackSubmitted();
      }
    } catch (err) {
      setStatus("error");
      setStatusMsg(err instanceof Error ? err.message : "Failed to record feedback.");
    }
  }

  return (
    <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {isFalsePositive && (
        <div
          style={{
            padding: "10px 14px",
            background: "rgba(82, 183, 136, 0.12)",
            border: "1px solid rgba(82, 183, 136, 0.35)",
            borderRadius: "var(--radius-sm)",
            fontSize: 13,
            color: "var(--low)",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <span>✓</span>
          <span>
            <strong>Confirmed False Positive:</strong> Risk score has been down-weighted in the queue.
            {existingReason && <span style={{ opacity: 0.9 }}> Reason: "{existingReason}"</span>}
          </span>
        </div>
      )}

      <div>
        <label style={{ fontSize: 13, color: "var(--muted)", display: "block", marginBottom: 6 }}>
          Investigator False-Positive Justification (POST /feedback):
        </label>
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={3}
          style={{
            width: "100%",
            boxSizing: "border-box",
            background: "var(--bg-subtle)",
            color: "var(--ink)",
            border: "1px solid var(--line)",
            borderRadius: "var(--radius-sm)",
            padding: "10px 12px",
            fontSize: 13,
            lineHeight: 1.5,
            outline: "none",
          }}
          placeholder="Document why this activity pattern is benign or expected for this account..."
        />
      </div>

      <div>
        <div style={{ fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>
          Quick justification presets:
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {PRESETS.map((p) => (
            <button
              key={p}
              type="button"
              className="chip"
              onClick={() => setReason(p)}
              style={{ fontSize: 11 }}
            >
              {p.split(":")[0]}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 4 }}>
        <button
          type="submit"
          disabled={status === "loading"}
          style={{
            background: "transparent",
            color: "var(--high)",
            border: "1px solid var(--high)",
            borderRadius: "var(--radius-sm)",
            padding: "8px 16px",
            fontSize: 13,
            fontWeight: 500,
            cursor: status === "loading" ? "not-allowed" : "pointer",
            transition: "all 0.2s ease",
          }}
        >
          {status === "loading" ? "Recording…" : "Mark as False Positive"}
        </button>

        {status === "success" && (
          <span className="mono" style={{ fontSize: 12, color: "var(--low)" }}>
            ✓ {statusMsg}
          </span>
        )}
        {status === "error" && (
          <span className="mono" style={{ fontSize: 12, color: "var(--critical)" }}>
            ✕ {statusMsg}
          </span>
        )}
      </div>
    </form>
  );
}
