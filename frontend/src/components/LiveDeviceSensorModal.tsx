import { useState, useEffect, useCallback, useRef } from "react";
import { postTelemetry } from "../api";

interface LiveDeviceSensorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSensorUpdate?: (userName: string, riskScore: number) => void;
}

// Automatically detect OS, kernel/platform, and device hardware model from browser client hints
function detectHardwareProfile(): { deviceName: string; osKernel: string; role: string; deviceId: string } {
  const ua = navigator.userAgent;
  let os = "Linux";
  let device = "Desktop Workstation";

  if (/Android/i.test(ua)) {
    os = "Android OS (Linux Kernel)";
    const match = ua.match(/Android\s([0-9.]+);\s*([^;)]+)/);
    device = match ? match[2].trim() : "Mobile Device";
  } else if (/iPhone|iPad/i.test(ua)) {
    os = "iOS (Darwin Kernel)";
    device = /iPad/i.test(ua) ? "Apple iPad" : "Apple iPhone";
  } else if (/Windows NT/i.test(ua)) {
    const ver = ua.match(/Windows NT ([0-9.]+)/);
    const winVer = ver && parseFloat(ver[1]) >= 10.0 ? "Windows 11/10" : "Windows";
    os = `${winVer} (NT Kernel)`;
    device = "PC Workstation";
  } else if (/Macintosh/i.test(ua)) {
    os = "macOS (XNU Kernel)";
    device = "Apple Mac";
  } else if (/Linux/i.test(ua)) {
    os = "Linux (GNU/Linux Kernel)";
    device = "Linux Workstation";
  }

  const cores = navigator.hardwareConcurrency ? `${navigator.hardwareConcurrency} Cores` : "";
  const mem = (navigator as any).deviceMemory ? `${(navigator as any).deviceMemory}GB RAM` : "";
  const hardwareSpec = [cores, mem].filter(Boolean).join(", ");

  const fullName = `${device} (${os})${hardwareSpec ? ` — ${hardwareSpec}` : ""}`;
  const rawId = `DEV-${os.replace(/[^a-zA-Z0-9]/g, "").slice(0, 4).toUpperCase()}-${Math.abs(
    fullName.split("").reduce((a, b) => ((a << 5) - a + b.charCodeAt(0)) | 0, 0)
  )
    .toString(16)
    .toUpperCase()
    .slice(0, 6)}`;

  return {
    deviceName: fullName,
    osKernel: os,
    role: "Enrolled Corporate Device",
    deviceId: rawId,
  };
}

export default function LiveDeviceSensorModal({
  isOpen,
  onClose,
  onSensorUpdate,
}: LiveDeviceSensorModalProps) {
  const [profile, setProfile] = useState<{ deviceName: string; osKernel: string; role: string; deviceId: string }>(
    () => detectHardwareProfile()
  );

  const [isActive, setIsActive] = useState(
    () => localStorage.getItem("silent_shift_sensor_active") === "true"
  );
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"sensor" | "privacy" | "terminal">("sensor");

  // Live sensor metrics
  const [riskScore, setRiskScore] = useState(12.0);
  const [severity, setSeverity] = useState<"low" | "medium" | "high" | "critical">("low");
  const [events, setEvents] = useState<Array<{ timestamp: string; event: string; category: string }>>([
    {
      timestamp: new Date().toISOString().replace("Z", ""),
      event: `Hardware sensor initialized for ${profile.deviceName}`,
      category: "baseline",
    },
  ]);
  const [cusumPoints, setCusumPoints] = useState<Array<{ time: string; timestamp: string; value: number; label: string; event: string }>>([
    {
      time: new Date().toLocaleTimeString(),
      timestamp: new Date().toISOString().replace("Z", ""),
      value: 0.0,
      label: "BASELINE",
      event: "Device enrolled into continuous CUSUM monitoring",
    },
  ]);

  const awayStartTimeRef = useRef<number | null>(null);

  // Attempt high-entropy userAgentData async detection if available (Chrome / Edge / Android)
  useEffect(() => {
    if ((navigator as any).userAgentData?.getHighEntropyValues) {
      (navigator as any).userAgentData
        .getHighEntropyValues(["model", "platform", "platformVersion", "architecture"])
        .then((hints: any) => {
          if (hints.model || hints.platform) {
            const detectedModel = hints.model || "Corporate Workstation";
            const detectedPlatform = hints.platform || "OS";
            const detectedArch = hints.architecture ? ` (${hints.architecture})` : "";
            const newName = `${detectedModel} [${detectedPlatform}${detectedArch}]`;
            setProfile((prev) => ({
              ...prev,
              deviceName: newName,
              osKernel: `${detectedPlatform} ${hints.platformVersion || ""}`.trim(),
            }));
          }
        })
        .catch(() => {});
    }
  }, []);

  // Sync state to backend
  const syncTelemetry = useCallback(
    async (
      customEvents = events,
      customCusum = cusumPoints,
      score = riskScore,
      sev = severity
    ) => {
      const now = new Date();
      const isAfterHours = now.getHours() < 7 || now.getHours() >= 20;

      const payload = {
        user_id: profile.deviceId,
        date: now.toISOString().slice(0, 10),
        name: profile.deviceName,
        role: profile.role,
        team: "Hardware Endpoint",
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
            ? `Critical Exfiltration Anomaly on ${profile.deviceName}: Multi-vector exfiltration detected. Hardware USB connection and unauthorized external file transfer.`
            : score >= 50
            ? `Medium Behavioral Elevation: Moderate activity drift and off-task browsing detected on ${profile.deviceName}.`
            : `Routine Baseline Activity: ${profile.deviceName} enrolled and operating within expected behavioral boundaries.`,
        event_timeline: customEvents,
        is_false_positive: false,
        feedback_reason: "",
        last_updated: now.toISOString(),
      };

      try {
        await postTelemetry(payload);
        setStatusMessage("✓ Telemetry synced to central console");
        if (onSensorUpdate) onSensorUpdate(profile.deviceName, score);
      } catch (err: any) {
        setStatusMessage(`Sync notice: ${err.message}`);
      }
    },
    [events, cusumPoints, riskScore, severity, profile, onSensorUpdate]
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
            event: `Off-task navigation detected: external tab/window active for ${awaySeconds}s on ${profile.osKernel}`,
            category: "http",
          };
          const newCusumPoint = {
            time: now.toLocaleTimeString(),
            timestamp: now.toISOString().replace("Z", ""),
            value: 0.42,
            label: "SIGNAL",
            event: `Off-task window switch (${awaySeconds}s)`,
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
  }, [isActive, riskScore, events, cusumPoints, profile, syncTelemetry]);

  // Real WebUSB Hardware Insertion / Authorization
  const handleWebUsbScan = async () => {
    if (!(navigator as any).usb) {
      alert("WebUSB API is not supported in this browser. Try Google Chrome, Edge, or Android Chrome.");
      return;
    }

    try {
      // Triggers the real OS hardware authorization popup
      const device = await (navigator as any).usb.requestDevice({ filters: [] });
      const now = new Date();
      const vendorHex = device.vendorId ? `0x${device.vendorId.toString(16).padStart(4, "0")}` : "0x0000";
      const productHex = device.productId ? `0x${device.productId.toString(16).padStart(4, "0")}` : "0x0000";
      const prodName = device.productName || "Removable Flash Drive";
      const mfg = device.manufacturerName ? `${device.manufacturerName} ` : "";

      const newEvent = {
        timestamp: now.toISOString().replace("Z", ""),
        event: `Hardware USB Attached: ${mfg}${prodName} (VID: ${vendorHex}, PID: ${productHex}) on ${profile.osKernel}`,
        category: "device",
      };

      const newCusumPoint = {
        time: now.toLocaleTimeString(),
        timestamp: now.toISOString().replace("Z", ""),
        value: 0.85,
        label: "DEVICE",
        event: `USB Hardware attached: ${prodName}`,
      };

      const newScore = Math.min(100, Math.max(82.0, riskScore + 35.0));
      const newSev = newScore >= 80 ? "critical" : "high";

      setRiskScore(newScore);
      setSeverity(newSev);
      const updatedEvents = [newEvent, ...events];
      const updatedCusum = [...cusumPoints, newCusumPoint];
      setEvents(updatedEvents);
      setCusumPoints(updatedCusum);

      syncTelemetry(updatedEvents, updatedCusum, newScore, newSev);
    } catch (err: any) {
      if (err.name !== "NotFoundError") {
        setStatusMessage(`Hardware sensor notice: ${err.message}`);
      }
    }
  };

  // Real Local File Staging
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const now = new Date();
    const sizeKb = Math.round(file.size / 1024);
    const newEvent = {
      timestamp: now.toISOString().replace("Z", ""),
      event: `Sensitive file staging detected: "${file.name}" (${sizeKb} KB, MIME: ${file.type || "binary"}) on ${profile.osKernel}`,
      category: "file",
    };
    const newCusumPoint = {
      time: now.toLocaleTimeString(),
      timestamp: now.toISOString().replace("Z", ""),
      value: 0.92,
      label: "EXFILTRATION",
      event: `Staged file: ${file.name}`,
    };

    const newScore = Math.min(100, Math.max(89.0, riskScore + 35.0));
    const newSev = "critical";

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
          maxWidth: 720,
          background: "var(--panel)",
          border: "1px solid var(--line)",
          borderRadius: 12,
          boxShadow: "0 24px 48px rgba(0, 0, 0, 0.5)",
          display: "flex",
          flexDirection: "column",
          maxHeight: "92vh",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "18px 24px",
            borderBottom: "1px solid var(--line)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 22 }}>🛡️</span>
            <div>
              <h2 style={{ fontSize: 16, margin: 0, fontWeight: 600 }}>
                Enterprise Endpoint Telemetry & Device Enrollment
              </h2>
              <p style={{ margin: "2px 0 0", fontSize: 12, color: "var(--muted)" }}>
                Automatically detects hardware specification & streams real behavioral drift into the central UEBA console.
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

        {/* Tab Selector */}
        <div style={{ display: "flex", borderBottom: "1px solid var(--line)", background: "var(--bg-subtle)" }}>
          <button
            onClick={() => setActiveTab("sensor")}
            style={{
              flex: 1,
              padding: "10px 16px",
              background: activeTab === "sensor" ? "var(--panel)" : "transparent",
              border: "none",
              borderBottom: activeTab === "sensor" ? "2px solid var(--cyan)" : "none",
              color: activeTab === "sensor" ? "var(--cyan)" : "var(--muted)",
              fontWeight: 600,
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            📡 Live Device Sensor
          </button>
          <button
            onClick={() => setActiveTab("privacy")}
            style={{
              flex: 1,
              padding: "10px 16px",
              background: activeTab === "privacy" ? "var(--panel)" : "transparent",
              border: "none",
              borderBottom: activeTab === "privacy" ? "2px solid var(--cyan)" : "none",
              color: activeTab === "privacy" ? "var(--cyan)" : "var(--muted)",
              fontWeight: 600,
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            ⚖️ Privacy & Ethics Defense
          </button>
          <button
            onClick={() => setActiveTab("terminal")}
            style={{
              flex: 1,
              padding: "10px 16px",
              background: activeTab === "terminal" ? "var(--panel)" : "transparent",
              border: "none",
              borderBottom: activeTab === "terminal" ? "2px solid var(--cyan)" : "none",
              color: activeTab === "terminal" ? "var(--cyan)" : "var(--muted)",
              fontWeight: 600,
              fontSize: 12,
              cursor: "pointer",
            }}
          >
            💻 Laptop Native Agent
          </button>
        </div>

        {/* Tab 1: Live Sensor */}
        {activeTab === "sensor" && (
          <div style={{ padding: "20px 24px", overflowY: "auto", display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Auto-detected Hardware Badge */}
            <div
              style={{
                background: "var(--bg-subtle)",
                padding: 16,
                borderRadius: 8,
                border: "1px solid var(--line)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontSize: 11, fontWeight: 600, textTransform: "uppercase", color: "var(--cyan)" }}>
                  Auto-Discovered Device Hardware
                </span>
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
                    ● ENROLLED & STREAMING
                  </span>
                ) : (
                  <span className="mono" style={{ fontSize: 11, color: "var(--muted)" }}>
                    ○ NOT ENROLLED
                  </span>
                )}
              </div>

              <div style={{ fontSize: 15, fontWeight: 600, color: "var(--text)" }}>
                {profile.deviceName}
              </div>
              <div className="mono" style={{ fontSize: 11, color: "var(--muted)", marginTop: 2 }}>
                Device ID: {profile.deviceId} | OS Kernel: {profile.osKernel}
              </div>

              <div style={{ marginTop: 12, display: "flex", gap: 10, alignItems: "center" }}>
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
                    Authorize & Enroll This Device
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
                    Pause Telemetry
                  </button>
                )}
                {statusMessage && (
                  <span className="mono" style={{ fontSize: 11, color: "var(--low)" }}>
                    {statusMessage}
                  </span>
                )}
              </div>
            </div>

            {/* Hardware-Level Triggers */}
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
              <strong style={{ display: "block", fontSize: 12, textTransform: "uppercase", color: "var(--muted)", marginBottom: 10 }}>
                Test Real Hardware & Behavioral Triggers
              </strong>

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {/* Real WebUSB Hardware Prompt */}
                <div
                  style={{
                    padding: "12px 14px",
                    background: "var(--panel)",
                    borderRadius: 6,
                    border: "1px solid var(--line)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <strong style={{ fontSize: 13 }}>🔌 Physical USB Hardware Detection (WebUSB)</strong>
                    <div style={{ fontSize: 11, color: "var(--muted)" }}>
                      Requests native OS USB authorization to read real hardware VID/PID.
                    </div>
                  </div>
                  <button
                    onClick={handleWebUsbScan}
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
                    Authorize USB Scan
                  </button>
                </div>

                {/* Tab focus drift */}
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
                    <strong style={{ fontSize: 13 }}>🌐 Tab Switching & Off-Task Window Drift</strong>
                    <div style={{ fontSize: 11, color: "var(--muted)" }}>
                      Switch to another browser tab for 5 seconds and return.
                    </div>
                  </div>
                  <span className="mono" style={{ fontSize: 11, color: "var(--cyan)" }}>
                    Active (Auto)
                  </span>
                </div>

                {/* File Drop */}
                <div
                  style={{
                    padding: "10px 14px",
                    background: "var(--panel)",
                    borderRadius: 6,
                    border: "1px dashed var(--line)",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <strong style={{ fontSize: 13 }}>📁 Local File Staging Detection</strong>
                    <div style={{ fontSize: 11, color: "var(--muted)" }}>
                      Select any real file from your computer to test exfiltration staging.
                    </div>
                  </div>
                  <label
                    style={{
                      background: "var(--panel)",
                      border: "1px solid var(--line)",
                      color: "var(--text)",
                      padding: "6px 14px",
                      borderRadius: 6,
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Select File
                    <input type="file" onChange={handleFileUpload} style={{ display: "none" }} />
                  </label>
                </div>
              </div>

              {/* Score bar */}
              <div
                style={{
                  marginTop: 14,
                  padding: "10px 14px",
                  borderRadius: 6,
                  background: "rgba(0, 0, 0, 0.4)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <span style={{ fontSize: 11, color: "var(--muted)" }}>Live Fused Risk Score:</span>
                  <div style={{ fontSize: 20, fontWeight: 700, color: "var(--text)" }}>
                    {riskScore.toFixed(1)}/100{" "}
                    <span className="mono" style={{ fontSize: 11, textTransform: "uppercase" }}>
                      [{severity}]
                    </span>
                  </div>
                </div>
                <button
                  onClick={() => {
                    onClose();
                    window.location.href = `/#/case/${profile.deviceId}`;
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
                  Inspect Case in Queue →
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Privacy & Ethics Defense */}
        {activeTab === "privacy" && (
          <div style={{ padding: "20px 24px", overflowY: "auto", display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ fontSize: 13, lineHeight: 1.5, color: "var(--text)" }}>
              <strong>How Silent Shift Defends Employee Privacy & Security:</strong>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 10, fontSize: 12, color: "var(--muted)" }}>
              <div style={{ padding: 12, background: "var(--bg-subtle)", borderRadius: 6, border: "1px solid var(--line)" }}>
                <strong style={{ color: "var(--low)" }}>1. Zero Content Inspection & Zero Keystroke Logging:</strong>
                <div>Silent Shift monitors <em>metadata</em> (file size, domain visited, USB vendor ID), NEVER private messages, emails, keystrokes, or screen recordings.</div>
              </div>

              <div style={{ padding: 12, background: "var(--bg-subtle)", borderRadius: 6, border: "1px solid var(--line)" }}>
                <strong style={{ color: "var(--low)" }}>2. Dual-Baseline Fairness (No Black-Box Accusations):</strong>
                <div>Behavior is scored against the employee's own 90-day personal baseline AND peer cohorts. Small cohorts (&lt;5 members) automatically disclose transparent fallbacks to prevent bias.</div>
              </div>

              <div style={{ padding: 12, background: "var(--bg-subtle)", borderRadius: 6, border: "1px solid var(--line)" }}>
                <strong style={{ color: "var(--low)" }}>3. Human-in-the-Loop False Positive Calibration:</strong>
                <div>The engine does not take automated punitive actions. When an investigator marks legitimate activity, the 0.4x dampening factor instantly protects the employee from alert fatigue.</div>
              </div>

              <div style={{ padding: 12, background: "var(--bg-subtle)", borderRadius: 6, border: "1px solid var(--line)" }}>
                <strong style={{ color: "var(--low)" }}>4. Enterprise AUP & Permission Boundaries:</strong>
                <div>Operates strictly within corporate Acceptable Use Policies (AUP) and standard W3C browser permission prompts with explicit user consent.</div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Laptop Native Terminal Agent */}
        {activeTab === "terminal" && (
          <div style={{ padding: "20px 24px", overflowY: "auto", display: "flex", flexDirection: "column", gap: 14 }}>
            <div style={{ fontSize: 13, color: "var(--text)" }}>
              <strong>Run the Native EDR Sensor on Your Laptop:</strong>
            </div>
            <p style={{ fontSize: 12, color: "var(--muted)", margin: 0 }}>
              To monitor real OS desktop window titles, local Chrome history, and Linux/Mac storage mount points directly from your operating system:
            </p>

            <div
              className="mono"
              style={{
                fontSize: 12,
                background: "rgba(0, 0, 0, 0.4)",
                padding: "12px 14px",
                borderRadius: 6,
                border: "1px solid var(--line)",
                overflowX: "auto",
                whiteSpace: "nowrap",
                color: "var(--cyan)",
              }}
            >
              curl -sSL {window.location.origin}/agent.py | python3 -
            </div>

            <div style={{ fontSize: 11, color: "var(--muted)" }}>
              • Automatically discovers your host OS username and hostname via <code>getpass</code> &amp; <code>socket</code>.<br />
              • Zero manual name entry required — reads your real machine identity.<br />
              • Streams encrypted HTTPS telemetry back to the centralized dashboard.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
