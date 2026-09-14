import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchCase, type CaseDetail } from "../api";
import CusumChart from "../components/CusumChart";
import FeedbackControl from "../components/FeedbackControl";
import SeverityBadge from "../components/SeverityBadge";
import Timeline from "../components/Timeline";

export default function CasePage() {
  const { userId } = useParams();
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [error, setError] = useState("");

  const loadCaseData = () => {
    if (!userId) return;
    fetchCase(userId)
      .then(setDetail)
      .catch((err: Error) => setError(err.message));
  };

  useEffect(() => {
    loadCaseData();
    const interval = setInterval(loadCaseData, 2000);
    return () => clearInterval(interval);
  }, [userId]);

  if (error) {
    return (
      <main style={{ padding: 32, maxWidth: 1000, margin: "0 auto" }}>
        <div className="card" style={{ borderColor: "var(--critical)", background: "var(--critical-bg)" }}>
          <p style={{ color: "var(--critical)", margin: 0 }}>{error}</p>
          <div style={{ marginTop: 12 }}>
            <Link to="/" style={{ color: "var(--cyan)", fontSize: 13, textDecoration: "underline" }}>
              ← Return to Queue
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (!detail) {
    return (
      <main style={{ padding: 48, textAlign: "center", color: "var(--muted)" }} className="mono">
        Loading case forensic dossier…
      </main>
    );
  }

  return (
    <main style={{ padding: "28px 32px", maxWidth: 1200, margin: "0 auto", display: "grid", gap: 24, width: "100%", boxSizing: "border-box", overflowX: "hidden" }}>
      {/* Navigation & Header */}
      <div>
        <Link
          to="/"
          style={{
            color: "var(--muted)",
            fontSize: 13,
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            marginBottom: 16,
            transition: "color 0.2s",
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = "var(--ink)")}
          onMouseLeave={(e) => (e.currentTarget.style.color = "var(--muted)")}
        >
          ← Return to Ranked Queue
        </Link>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, flexWrap: "wrap" }}>
          <div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 12, flexWrap: "wrap" }}>
              <h1 style={{ margin: 0, fontSize: 26, fontWeight: 600 }}>{detail.name}</h1>
              <span className="mono" style={{ color: "var(--cyan)", fontSize: 14, background: "rgba(72, 202, 228, 0.1)", padding: "2px 8px", borderRadius: 4 }}>
                {detail.user_id}
              </span>
            </div>
            <div style={{ color: "var(--muted)", marginTop: 6, fontSize: 14 }}>
              Role: <strong style={{ color: "var(--ink-secondary)" }}>{detail.role}</strong>
              {detail.team && <span> · Team: <strong style={{ color: "var(--ink-secondary)" }}>{detail.team}</strong></span>}
              <span> · Last Scored: <span className="mono">{detail.last_updated}</span></span>
            </div>
          </div>

          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <SeverityBadge severity={detail.severity} />
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-end",
                padding: "8px 16px",
                background: "var(--bg-subtle)",
                border: "1px solid var(--line)",
                borderRadius: "var(--radius-sm)",
              }}
            >
              <span style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--muted)" }}>
                Fused Risk Score
              </span>
              <span className="mono" style={{ fontSize: 28, fontWeight: 700, color: "var(--ink)" }}>
                {detail.risk_score.toFixed(0)}
                <span style={{ fontSize: 14, color: "var(--muted)", fontWeight: 400 }}>/100</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Tri-Signal Breakdown Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 }}>
        {/* Self-Baseline Anomaly */}
        <div className="card" style={{ padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <span style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--muted)" }}>
              Self-Baseline (Isolation Forest)
            </span>
            <span className="mono" style={{ fontWeight: 600, fontSize: 16 }}>
              {detail.self_score.toFixed(2)}
            </span>
          </div>
          <div className="meter-bar-track">
            <div
              className="meter-bar-fill"
              style={{
                width: `${Math.min(100, detail.self_score * 100)}%`,
                background: detail.self_score >= 0.5 ? "var(--critical)" : "var(--low)",
              }}
            />
          </div>
          <div style={{ fontSize: 12, color: detail.self_score >= 0.5 ? "var(--critical)" : "var(--muted)", marginTop: 8 }}>
            {detail.self_score >= 0.5 ? "Significant deviation from personal history" : "Within learned personal activity bounds"}
          </div>
        </div>

        {/* Peer-Cohort Deviation */}
        <div className="card" style={{ padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <span style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--muted)" }}>
              Peer Cohort ({detail.cohort_used})
            </span>
            <span className="mono" style={{ fontWeight: 600, fontSize: 16 }}>
              {detail.peer_score.toFixed(2)}
            </span>
          </div>
          <div className="meter-bar-track">
            <div
              className="meter-bar-fill"
              style={{
                width: `${Math.min(100, detail.peer_score * 100)}%`,
                background: detail.peer_score >= 0.5 ? "var(--high)" : "var(--low)",
              }}
            />
          </div>
          <div style={{ fontSize: 12, color: detail.peer_score >= 0.5 ? "var(--high)" : "var(--muted)", marginTop: 8 }}>
            {detail.peer_score >= 0.5 ? "Anomalous vs cohort peer distribution" : "In line with cohort peer patterns"}
          </div>
        </div>

        {/* Temporal Drift (CUSUM) */}
        <div className="card" style={{ padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <span style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--muted)" }}>
              Temporal Drift (CUSUM)
            </span>
            <span className="mono" style={{ fontWeight: 600, fontSize: 16 }}>
              {detail.drift_score.toFixed(2)}
            </span>
          </div>
          <div className="meter-bar-track">
            <div
              className="meter-bar-fill"
              style={{
                width: `${Math.min(100, detail.drift_score * 100)}%`,
                background: detail.drift_score >= 0.25 ? "var(--cyan)" : "var(--low)",
              }}
            />
          </div>
          <div style={{ fontSize: 12, color: detail.drift_score >= 0.25 ? "var(--cyan)" : "var(--muted)", marginTop: 8 }}>
            {detail.drift_score >= 0.25 ? "Sustained upward behavioral drift detected" : "No sustained cumulative trend"}
          </div>
        </div>
      </div>

      {/* "Why this account now" Explanation Panel */}
      <section className="card">
        <h2 style={{ marginTop: 0, fontSize: 16, fontWeight: 600, marginBottom: 12 }}>
          Why This Account Now (Investigator Assessment)
        </h2>
        <p style={{ lineHeight: 1.6, fontSize: 14, color: "var(--ink-secondary)", margin: 0 }}>
          {detail.explanation_text}
        </p>

        {/* Fallback Disclosure per Section 7.2 of the specification */}
        {detail.fallback_applied && (
          <div className="fallback-banner" style={{ marginTop: 14 }}>
            <strong>Department Fallback Disclosed:</strong> Due to small role cohort size (&lt; 5 members),
            peer comparison automatically fell back to the department-level cohort.
            This prevents small-sample skew and transparently discloses the broader reference baseline.
          </div>
        )}
      </section>

      {/* CUSUM Accumulation Chart */}
      <CusumChart path={detail.cusum_path} timeline={detail.event_timeline} />

      {/* Forensic Timeline */}
      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 16 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>Forensic Chronological Timeline</h2>
            <p style={{ margin: "4px 0 0 0", fontSize: 12, color: "var(--muted)" }}>
              Chronological drill-down of security events and baseline elevation triggers.
            </p>
          </div>
          <span className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>
            {detail.event_timeline.length} events logged
          </span>
        </div>
        <Timeline events={detail.event_timeline} />
      </section>

      {/* Feedback Control */}
      <section className="card">
        <h2 style={{ marginTop: 0, fontSize: 16, fontWeight: 600, marginBottom: 6 }}>
          Investigator Feedback &amp; Signal Calibration
        </h2>
        <p style={{ fontSize: 13, color: "var(--muted)", marginTop: 0, marginBottom: 16 }}>
          Marking an account as a false positive immediately down-weights this signal combination in the fusion engine, mitigating analyst fatigue.
        </p>
        <FeedbackControl
          userId={detail.user_id}
          isFalsePositive={detail.is_false_positive}
          existingReason={detail.feedback_reason}
          onFeedbackSubmitted={loadCaseData}
        />
      </section>

      {/* Section 10 Governance: Audit-the-Auditor */}
      <section className="card" style={{ borderColor: "rgba(34, 181, 191, 0.3)", background: "rgba(15, 23, 42, 0.6)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 14 }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
              <span>👁️</span> Admin Access Audit Trail ("Audit-the-Auditor")
            </h2>
            <p style={{ margin: "4px 0 0 0", fontSize: 12, color: "var(--muted)" }}>
              Section 10 Governance &amp; Anti-Surveillance: Every administrator query into an employee's case dossier is immutably logged to prevent unauthorized internal snooping.
            </p>
          </div>
          <span style={{ fontSize: 11, padding: "2px 8px", borderRadius: 4, background: "rgba(34, 181, 191, 0.15)", color: "var(--cyan)", fontWeight: 600 }}>
            SECTION 10 COMPLIANT
          </span>
        </div>

        {detail.access_audit_log && detail.access_audit_log.length > 0 ? (
          <div style={{ display: "grid", gap: 8 }}>
            {detail.access_audit_log.map((entry) => (
              <div
                key={entry.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 12px",
                  background: "rgba(0, 0, 0, 0.25)",
                  borderRadius: 6,
                  border: "1px solid var(--line)",
                  fontSize: 12,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span className="mono" style={{ color: "var(--cyan)", fontWeight: 600 }}>
                    {entry.investigator_id}
                  </span>
                  <span style={{ color: "var(--muted)" }}>→</span>
                  <span style={{ color: "var(--ink-secondary)" }}>{entry.action}</span>
                </div>
                <span className="mono" style={{ color: "var(--muted)", fontSize: 11 }}>
                  {new Date(entry.timestamp).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ fontSize: 12, color: "var(--muted)", fontStyle: "italic" }}>
            First recorded administrative access logged for this session.
          </div>
        )}
      </section>
    </main>
  );
}
