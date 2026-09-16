import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchQueue, type QueueItem } from "../api";
import SeverityBadge from "../components/SeverityBadge";

export default function QueuePage() {
  const [rows, setRows] = useState<QueueItem[]>([]);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const navigate = useNavigate();

  useEffect(() => {
    const loadQueue = () => {
      fetchQueue()
        .then((data) => {
          const map = new Map<string, QueueItem>();
          for (const item of data) {
            if (!map.has(item.user_id)) {
              map.set(item.user_id, item);
            }
          }
          setRows(Array.from(map.values()).sort((a, b) => b.risk_score - a.risk_score));
          setError("");
        })
        .catch((err: Error) => setError(err.message));
    };
    loadQueue();
    const interval = setInterval(loadQueue, 2000);
    return () => clearInterval(interval);
  }, []);

  const filteredRows = useMemo(() => {
    return rows.filter((row) => {
      const matchesSearch =
        search === "" ||
        row.name.toLowerCase().includes(search.toLowerCase()) ||
        row.user_id.toLowerCase().includes(search.toLowerCase()) ||
        row.role.toLowerCase().includes(search.toLowerCase());

      const matchesSeverity =
        severityFilter === "all" || row.severity === severityFilter;

      return matchesSearch && matchesSeverity;
    });
  }, [rows, search, severityFilter]);

  const kpis = useMemo(() => {
    const critical = rows.filter((r) => r.severity === "critical").length;
    const high = rows.filter((r) => r.severity === "high").length;
    const medium = rows.filter((r) => r.severity === "medium").length;
    const fallbacks = rows.filter((r) => r.fallback_applied).length;
    return { total: rows.length, critical, high, medium, fallbacks };
  }, [rows]);

  return (
    <main style={{ padding: "28px 32px", maxWidth: 1200, margin: "0 auto", width: "100%" }}>
      {/* Header section */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24, flexWrap: "wrap", gap: 16 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
            <h1 style={{ fontSize: 24, fontWeight: 600, margin: 0, letterSpacing: "-0.02em" }}>
              Ranked Risk Queue
            </h1>
            <span
              className="mono"
              style={{
                fontSize: 11,
                padding: "2px 8px",
                borderRadius: 4,
                background: "rgba(82, 183, 136, 0.15)",
                color: "var(--low)",
                border: "1px solid rgba(82, 183, 136, 0.3)",
              }}
            >
              ● DUAL-BASELINE ENGINE ACTIVE
            </span>
          </div>
          <p style={{ color: "var(--muted)", margin: 0, fontSize: 14 }}>
            Prioritized insider risk queue scored across self-baseline and peer-cohort baselines with small-cohort fallback disclosures.
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">Flagged Accounts</div>
          <div className="kpi-val">{kpis.total}</div>
        </div>
        <div className="kpi-card critical">
          <div className="kpi-label">Critical Tier</div>
          <div className="kpi-val" style={{ color: "var(--critical)" }}>{kpis.critical}</div>
        </div>
        <div className="kpi-card high">
          <div className="kpi-label">High Tier</div>
          <div className="kpi-val" style={{ color: "var(--high)" }}>{kpis.high}</div>
        </div>
        <div className="kpi-card medium">
          <div className="kpi-label">Medium Tier</div>
          <div className="kpi-val" style={{ color: "var(--medium)" }}>{kpis.medium}</div>
        </div>
        <div className="kpi-card fallback">
          <div className="kpi-label">Fallbacks Disclosed</div>
          <div className="kpi-val" style={{ color: "var(--cyan)" }}>{kpis.fallbacks}</div>
        </div>
      </div>

      {/* Toolbar: Search and Filter Chips */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 12,
          marginBottom: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 12, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>
            Filter:
          </span>
          {(["all", "critical", "high", "medium"] as const).map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`chip ${severityFilter === sev ? "active" : ""}`}
              type="button"
            >
              {sev.charAt(0).toUpperCase() + sev.slice(1)}
              {sev !== "all" && (
                <span style={{ marginLeft: 6, opacity: 0.7 }}>
                  ({rows.filter((r) => r.severity === sev).length})
                </span>
              )}
            </button>
          ))}
        </div>

        <input
          type="text"
          className="input-search"
          placeholder="Search name, ID, or role…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 260 }}
        />
      </div>

      {error ? (
        <div className="card" style={{ borderColor: "var(--critical)", background: "var(--critical-bg)", marginBottom: 20 }}>
          <p style={{ color: "var(--critical)", margin: 0, fontWeight: 500 }}>
            Could not load /queue. Start the server using: <code className="mono">bash frontend/start.sh</code>
          </p>
          <div className="mono" style={{ fontSize: 12, color: "var(--muted)", marginTop: 6 }}>{error}</div>
        </div>
      ) : null}

      {/* Table */}
      <div style={{ overflowX: "auto" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>Account</th>
              <th>Role & Team</th>
              <th>Severity</th>
              <th>Risk Score</th>
              <th>Cohort Context</th>
              <th>Last Scored</th>
              <th style={{ textAlign: "right" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((row) => (
              <tr key={row.user_id} onClick={() => navigate(`/case/${row.user_id}`)}>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                    <span style={{ fontWeight: 600, color: "var(--ink)" }}>{row.name}</span>
                    {row.is_false_positive && (
                      <span
                        className="mono"
                        style={{
                          fontSize: 10,
                          padding: "1px 6px",
                          borderRadius: 4,
                          background: "rgba(82, 183, 136, 0.15)",
                          color: "var(--low)",
                          border: "1px solid rgba(82, 183, 136, 0.35)",
                          fontWeight: 600,
                        }}
                      >
                        ✓ CALIBRATED FP
                      </span>
                    )}
                  </div>
                  <div className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>
                    {row.user_id}
                  </div>
                </td>
                <td>
                  <div>{row.role}</div>
                  {row.team && (
                    <div style={{ fontSize: 12, color: "var(--muted)" }}>Team: {row.team}</div>
                  )}
                </td>
                <td>
                  <SeverityBadge severity={row.severity} />
                </td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span className="mono" style={{ fontWeight: 600, fontSize: 15, width: 36 }}>
                      {row.risk_score.toFixed(0)}
                    </span>
                    <div style={{ width: 70, height: 5, background: "var(--line)", borderRadius: 999, overflow: "hidden" }}>
                      <div
                        style={{
                          width: `${Math.min(100, row.risk_score)}%`,
                          height: "100%",
                          background:
                            row.severity === "critical"
                              ? "var(--critical)"
                              : row.severity === "high"
                              ? "var(--high)"
                              : row.severity === "medium"
                              ? "var(--medium)"
                              : "var(--low)",
                        }}
                      />
                    </div>
                  </div>
                </td>
                <td>
                  {row.fallback_applied ? (
                    <span
                      className="mono"
                      style={{
                        fontSize: 11,
                        background: "rgba(245, 166, 35, 0.12)",
                        color: "var(--high)",
                        border: "1px solid rgba(245, 166, 35, 0.3)",
                        padding: "2px 7px",
                        borderRadius: 4,
                      }}
                    >
                      Dept Fallback
                    </span>
                  ) : (
                    <span className="mono" style={{ fontSize: 12, color: "var(--muted)" }}>
                      Role Cohort
                    </span>
                  )}
                </td>
                <td className="mono" style={{ fontSize: 13, color: "var(--muted)" }}>
                  {row.last_updated}
                </td>
                <td style={{ textAlign: "right" }}>
                  <Link
                    to={`/case/${row.user_id}`}
                    style={{
                      color: "var(--cyan)",
                      fontSize: 13,
                      fontWeight: 500,
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    Investigate →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {!error && filteredRows.length === 0 ? (
        <div className="card" style={{ textAlign: "center", padding: "48px 24px", marginTop: 20 }}>
          <p style={{ color: "var(--muted)", margin: 0, fontSize: 15 }}>
            {search || severityFilter !== "all"
              ? "No accounts match the current search or severity filter."
              : "No flagged accounts in the current scores table."}
          </p>
        </div>
      ) : null}
    </main>
  );
}
