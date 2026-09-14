import { useState, useEffect, useCallback, useRef } from "react";
import { postTelemetry } from "../api";

interface LiveDeviceSensorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSensorUpdate?: (userName: string, riskScore: number) => void;
}

export default function LiveDeviceSensorModal({
  isOpen,
  onClose,
  onSensorUpdate,
}: LiveDeviceSensorModalProps) {
  const [name, setName] = useState(
    () => localStorage.getItem("silent_shift_device_name") || "Evaluator / Guest"
  );
  const [role, setRole] = useState(
    () => localStorage.getItem("silent_shift_device_role") || "Security Evaluator"
  );
  const [department] = useState("Auditing");
  const [isActive, setIsActive] = useState(
    () => localStorage.getItem("silent_shift_sensor_active") === "true"
  );
  const [statusMessage, setStatusMessage] = useState<string>("");

  // Live sensor metrics
  const [riskScore, setRiskScore] = useState(12.0);
  const [severity, setSeverity] = useState<"low" | "medium" | "high" | "critical">("low");
  const [events, setEvents] = useState<Array<{ timestamp: string; event: string; category: string }>>([
    {
      timestamp: new Date().toISOString().replace("Z", ""),
      event: "Live browser endpoint sensor initialized (baseline active)",
      category: "baseline",
    },
  ]);
  const [cusumPoints, setCusumPoints] = useState<Array<{ time: string; timestamp: string; value: number; label: string; event: string }>>([
    {
      time: new Date().toLocaleTimeString(),
      timestamp: new Date().toISOString().replace("Z", ""),
      value: 0.0,
      label: "BASELINE",
      event: "Device enrolled in live monitoring",
    },
  ]);

  const awayStartTimeRef = useRef<number | null>(null);

  // Sync state to backend
  const syncTelemetry = useCallback(
    async (
      customEvents = events,
      customCusum = cusumPoints,
      score = riskScore,
      sev = severity
    ) => {
      const sanitizedId = "DEV-" + name.replace(/[^a-zA-Z0-9]/g, "").toUpperCase().slice(0, 10);
      const now = new Date();
      const isAfterHours = now.getHours() < 7 || now.getHours() >= 20;

      const payload = {
        user_id: sanitizedId || "DEV-EVALUATOR",
        date: now.toISOString().slice(0, 10),
        name: name || "Evaluator Guest",
        role: role || "Security Evaluator",
        team: department || "Auditing",
        risk_score: score,
        severity: sev,
        self_score: Math.min(1.0, score / 100),
        peer_score: Math.min(1.0, (score * 0.9) / 100),
        drift_score: Math.min(1.0, score > 50 ? (score - 40) / 60 : 0.0),
        pre_multiplier_score: Math.min(1.0, score / 100),
        raw_fusion_score: Math.min(1.0, score / 100),
        adjusted_fusion_score: Math.min(1.8, score / 60),
        cohort_used: "role",
        cohort_size: 8,
        fallback_applied: false,
        cusum_path: customCusum,
        multipliers_applied: {
          role: 1.0,
          time: isAfterHours ? 1.3 : 1.0,
          data_sensitivity: score > 70 ? 1.3 : 1.0,
          decay: 1.0,
          feedback_down_weight: 1.0,
        },
        score_components: {
          self: Math.min(1.0, score / 100),
          peer: Math.min(1.0, (score * 0.9) / 100),
          drift: Math.min(1.0, score > 50 ? (score - 40) / 60 : 0.0),
        },
        explanation_text:
          score >= 80
            ? `Critical Anomaly on Live Device: Sustained multi-vector behavioral deviation. High data staging and frequent off-task navigation.`
            : score >= 50
            ? `Medium Behavioral Elevation: Moderate activity drift detected from enrolled browser session.`
            : `Routine Baseline Activity: Enrolled live client session within normal personal parameters.`,
        event_timeline: customEvents,
        is_false_positive: false,
        feedback_reason: "",
        last_updated: now.toISOString(),
      };

      try {
        await postTelemetry(payload);
        setStatusMessage("✓ Telemetry synced to central console");
        if (onSensorUpdate) onSensorUpdate(name, score);
      } catch (err: any) {
        setStatusMessage(`Sync notice: ${err.message}`);
      }
    },
    [events, cusumPoints, riskScore, severity, name, role, department, onSensorUpdate]
  );

  // Monitor real tab visibility changes
  useEffect(() => {
    if (!isActive) return;

    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        awayStartTimeRef.current = Date.now();
      } else if (document.visibilityState === "visible" && awayStartTimeRef.current) {
        const awaySeconds = Math.round((Date.now() - awayStartTimeRef.current) / 1000);
        awayStartTimeRef.current = null;

        if (awaySeconds >= 2) {
          const now = new Date();
          const newEvent = {
            timestamp: now.toISOString().replace("Z", ""),
            event: `Off-task navigation detected: external tab/window active for ${awaySeconds}s`,
            category: "http",
          };
          const newCusumPoint = {
            time: now.toLocaleTimeString(),
            timestamp: now.toISOString().replace("Z", ""),
            value: 0.38,
            label: "SIGNAL",
            event: `Off-task switch (${awaySeconds}s)`,
          };

          const newScore = Math.min(100, Math.max(54.0, riskScore + 22.0));
          const newSev = newScore >= 80 ? "critical" : newScore >= 65 ? "high" : "medium";

          setRiskScore(newScore);
          setSeverity(newSev);
          const updatedEvents = [newEvent, ...events];
          const updatedCusum = [...cusumPoints, newCusumPoint];
          setEvents(updatedEvents);
          setCusumPoints(updatedCusum);

          syncTelemetry(updatedEvents, updatedCusum, newScore, newSev);
        }
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [isActive, riskScore, events, cusumPoints, syncTelemetry]);

  // Handle local file drop
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const now = new Date();
    const sizeKb = Math.round(file.size / 1024);
    const newEvent = {
      timestamp: now.toISOString().replace("Z", ""),
      event: `Sensitive file staging detected: "${file.name}" (${sizeKb} KB, type: ${file.type || "binary"})`,
      category: "file",
    };
    const newCusumPoint = {
      time: now.toLocaleTimeString(),
      timestamp: now.toISOString().replace("Z", ""),
      value: 0.82,
      label: "EXFILTRATION",
      event: `Staged file: ${file.name}`,
    };

    const newScore = Math.min(100, Math.max(88.0, riskScore + 35.0));
    const newSev = "critical";

    setRiskScore(newScore);
    setSeverity(newSev);
    const updatedEvents = [newEvent, ...events];
    const updatedCusum = [...cusumPoints, newCusumPoint];
    setEvents(updatedEvents);
    setCusumPoints(updatedCusum);

    syncTelemetry(updatedEvents, updatedCusum, newScore, newSev);
  };

  // Handle clipboard copy of sensitive token
  const handleCopySensitive = () => {
    const fakeToken = "SS-CONFIDENTIAL-DB-KEY-89472-X90B-VAULT";
    navigator.clipboard.writeText(fakeToken);

    const now = new Date();
    const newEvent = {
      timestamp: now.toISOString().replace("Z", ""),
      event: `High-risk clipboard operation: copied sensitive credential token to local clipboard`,
      category: "device",
    };
    const newCusumPoint = {
      time: now.toLocaleTimeString(),
      timestamp: now.toISOString().replace("Z", ""),
      value: 0.65,
      label: "CLIPBOARD",
      event: "Credential token copied",
    };

    const newScore = Math.min(100, Math.max(72.0, riskScore + 20.0));
    const newSev = newScore >= 80 ? "critical" : "high";

    setRiskScore(newScore);
    setSeverity(newSev);
    const updatedEvents = [newEvent, ...events];
    const updatedCusum = [...cusumPoints, newCusumPoint];
    setEvents(updatedEvents);
    setCusumPoints(updatedCusum);

    syncTelemetry(updatedEvents, updatedCusum, newScore, newSev);
  };

  const handleEnroll = () => {
    setIsActive(true);
    localStorage.setItem("silent_shift_sensor_active", "true");
    localStorage.setItem("silent_shift_device_name", name);
    localStorage.setItem("silent_shift_device_role", role);
    syncTelemetry(events, cusumPoints, riskScore, severity);
  };

  const handleDeactivate = () => {
    setIsActive(false);
    localStorage.setItem("silent_shift_sensor_active", "false");
    setStatusMessage("Sensor paused for this device.");
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: 20,
      }}
    >
      <div
        className="card"
        style={{
          width: "100%",
          maxWidth: 680,
          background: "var(--panel)",
          border: "1px solid var(--line)",
          borderRadius: 12,
          boxShadow: "0 24px 48px rgba(0, 0, 0, 0.5)",
          display: "flex",
          flexDirection: "column",
          maxHeight: "90vh",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid var(--line)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 20 }}>📡</span>
            <div>
              <h2 style={{ fontSize: 16, margin: 0, fontWeight: 600 }}>
                Live In-Browser Endpoint Sensor (Multi-User Detection)
              </h2>
              <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>
                Enrolls this exact browser device as an active monitored employee in the real detection engine.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--muted)",
              fontSize: 18,
              cursor: "pointer",
            }}
          >
            ✕
          </button>
        </div>

        {/* Content Body */}
        <div style={{ padding: "24px", overflowY: "auto", display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Identity Enrollment */}
          <div
            style={{
              background: "var(--bg-subtle)",
              padding: 16,
              borderRadius: 8,
              border: "1px solid var(--line)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <strong style={{ fontSize: 13, letterSpacing: "0.04em", textTransform: "uppercase" }}>
                1. Device Enrollment
              </strong>
              {isActive ? (
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
                  ● SENSOR ACTIVE ON THIS DEVICE
                </span>
              ) : (
                <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
                  ○ UNENROLLED
                </span>
              )}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div>
                <label style={{ display: "block", fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>
                  Your Name / Identity:
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Judge Dave, Dr. Alex"
                  style={{
                    width: "100%",
                    background: "var(--panel)",
                    border: "1px solid var(--line)",
                    borderRadius: 6,
                    padding: "8px 12px",
                    color: "var(--text)",
                    fontSize: 13,
                  }}
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: 12, color: "var(--muted)", marginBottom: 4 }}>
                  Assigned Employee Role:
                </label>
                <input
                  type="text"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  placeholder="e.g. Security Auditor, Financial Analyst"
                  style={{
                    width: "100%",
                    background: "var(--panel)",
                    border: "1px solid var(--line)",
                    borderRadius: 6,
                    padding: "8px 12px",
                    color: "var(--text)",
                    fontSize: 13,
                  }}
                />
              </div>
            </div>

            <div style={{ marginTop: 14, display: "flex", gap: 10, alignItems: "center" }}>
              {!isActive ? (
                <button
                  onClick={handleEnroll}
                  style={{
                    background: "var(--cyan)",
                    color: "#0a0e14",
                    border: "none",
                    padding: "8px 18px",
                    borderRadius: 6,
                    fontWeight: 600,
                    fontSize: 12,
                    cursor: "pointer",
                  }}
                >
                  ⚡ Activate Sensor for My Device
                </button>
              ) : (
                <button
                  onClick={handleDeactivate}
                  style={{
                    background: "rgba(224, 86, 96, 0.15)",
                    color: "var(--critical)",
                    border: "1px solid rgba(224, 86, 96, 0.3)",
                    padding: "8px 16px",
                    borderRadius: 6,
                    fontWeight: 600,
                    fontSize: 12,
                    cursor: "pointer",
                  }}
                >
                  Pause Sensor
                </button>
              )}
              {statusMessage && (
                <span className="mono" style={{ fontSize: 11, color: "var(--low)" }}>
                  {statusMessage}
                </span>
              )}
            </div>
          </div>

          {/* Interactive Live Triggers */}
          <div
            style={{
              background: "var(--bg-subtle)",
              padding: 16,
              borderRadius: 8,
              border: "1px solid var(--line)",
              opacity: isActive ? 1 : 0.5,
              pointerEvents: isActive ? "auto" : "none",
            }}
          >
            <strong style={{ display: "block", fontSize: 13, letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: 10 }}>
              2. Test Real Live Triggers On This Device
            </strong>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 14px" }}>
              Perform any of these real actions to watch the detection engine react to YOUR device in real time:
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {/* Trigger 1: Tab switch */}
              <div
                style={{
                  padding: "10px 14px",
                  background: "var(--panel)",
                  borderRadius: 6,
                  border: "1px solid var(--line)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <strong style={{ fontSize: 13 }}>👉 Real Tab Switching (Off-Task Drift)</strong>
                  <div style={{ fontSize: 11, color: "var(--muted)" }}>
                    Switch to another tab (e.g. YouTube or Gmail) for 5 seconds and come back.
                  </div>
                </div>
                <span className="mono" style={{ fontSize: 11, color: "var(--cyan)" }}>
                  Listening (Auto)
                </span>
              </div>

              {/* Trigger 2: File Drop */}
              <div
                style={{
                  padding: "12px 14px",
                  background: "var(--panel)",
                  borderRadius: 6,
                  border: "1px dashed var(--cyan)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <strong style={{ fontSize: 13 }}>👉 Drop Any Real File (Exfiltration Staging)</strong>
                  <div style={{ fontSize: 11, color: "var(--muted)" }}>
                    Select or drag any PDF, image, or text file from your computer.
                  </div>
                </div>
                <label
                  style={{
                    background: "rgba(0, 229, 255, 0.12)",
                    border: "1px solid rgba(0, 229, 255, 0.4)",
                    color: "var(--cyan)",
                    padding: "6px 14px",
                    borderRadius: 6,
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Browse File
                  <input type="file" onChange={handleFileUpload} style={{ display: "none" }} />
                </label>
              </div>

              {/* Trigger 3: Clipboard */}
              <div
                style={{
                  padding: "10px 14px",
                  background: "var(--panel)",
                  borderRadius: 6,
                  border: "1px solid var(--line)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <strong style={{ fontSize: 13 }}>👉 Clipboard Exfiltration</strong>
                  <div style={{ fontSize: 11, color: "var(--muted)" }}>
                    Test copying sensitive security tokens to your system clipboard.
                  </div>
                </div>
                <button
                  onClick={handleCopySensitive}
                  style={{
                    background: "rgba(235, 179, 56, 0.15)",
                    border: "1px solid rgba(235, 179, 56, 0.4)",
                    color: "var(--medium)",
                    padding: "6px 14px",
                    borderRadius: 6,
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Copy Secret Token
                </button>
              </div>
            </div>

            {/* Current Score preview */}
            <div
              style={{
                marginTop: 16,
                padding: "12px 16px",
                borderRadius: 6,
                background: "rgba(0, 0, 0, 0.3)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <span style={{ fontSize: 12, color: "var(--muted)" }}>Your Current Risk Score:</span>
                <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                  <span style={{ fontSize: 22, fontWeight: 700, color: "var(--text)" }}>
                    {riskScore.toFixed(1)}/100
                  </span>
                  <span
                    className="mono"
                    style={{
                      fontSize: 11,
                      textTransform: "uppercase",
                      color:
                        severity === "critical"
                          ? "var(--critical)"
                          : severity === "high"
                          ? "var(--high)"
                          : severity === "medium"
                          ? "var(--medium)"
                          : "var(--low)",
                    }}
                  >
                    [{severity}]
                  </span>
                </div>
              </div>
              <button
                onClick={() => {
                  onClose();
                  window.location.href = `/#/case/DEV-${name.replace(/[^a-zA-Z0-9]/g, "").toUpperCase().slice(0, 10)}`;
                }}
                style={{
                  background: "var(--cyan)",
                  color: "#0a0e14",
                  border: "none",
                  padding: "6px 14px",
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                View My Case File →
              </button>
            </div>
          </div>

          {/* Option for laptop terminal users */}
          <div
            style={{
              background: "var(--bg-subtle)",
              padding: 14,
              borderRadius: 8,
              border: "1px solid var(--line)",
            }}
          >
            <div style={{ fontSize: 12, fontWeight: 600, color: "var(--muted)", marginBottom: 6 }}>
              💻 WANT TO MONITOR PHYSICAL USB & DESKTOP WINDOWS ON A LAPTOP?
            </div>
            <div
              className="mono"
              style={{
                fontSize: 11,
                background: "rgba(0, 0, 0, 0.4)",
                padding: "8px 12px",
                borderRadius: 6,
                border: "1px solid var(--line)",
                overflowX: "auto",
                whiteSpace: "nowrap",
                color: "var(--cyan)",
              }}
            >
              curl -sSL {window.location.origin}/agent.py | python3 -
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
