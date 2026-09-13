import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { simulateThreat } from "../api";

interface ThreatSimulatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export default function ThreatSimulatorModal({ isOpen, onClose, onSuccess }: ThreatSimulatorModalProps) {
  const navigate = useNavigate();
  const [name, setName] = useState("Mohammed Shamaz");
  const [role, setRole] = useState("Engineer");
  const [site, setSite] = useState("https://wetransfer.com/upload");
  const [file, setFile] = useState("confidential_customer_records.sql");
  const [email, setEmail] = useState("personal_leak@gmail.com");
  const [afterHours, setAfterHours] = useState(true);
  const [usb, setUsb] = useState(true);
  const [cloudUpload, setCloudUpload] = useState(true);
  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [error, setError] = useState("");

  if (!isOpen) return null;

  async function handleSimulate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setStatusMsg("1/4: Injecting activity logs into CERT dataset...");

    try {
      setTimeout(() => setStatusMsg("2/4: Running Isolation Forest self-baseline & Cohort z-scores..."), 800);
      setTimeout(() => setStatusMsg("3/4: Accumulating CUSUM temporal drift & applying multipliers..."), 2000);
      setTimeout(() => setStatusMsg("4/4: Generating Section 7.2 explanation & persisting alert..."), 3500);

      const res = await simulateThreat({
        name,
        role,
        site,
        file,
        email,
        after_hours: afterHours,
        usb,
        cloud_upload: cloudUpload,
      });

      if (res.ok && res.user_id) {
        setStatusMsg("Detection complete! Flagged as " + res.severity.toUpperCase());
        setTimeout(() => {
          setLoading(false);
          onClose();
          if (onSuccess) onSuccess();
          navigate(`/case/${encodeURIComponent(res.user_id)}`);
        }, 1000);
      } else {
        throw new Error("Simulation completed without user ID");
      }
    } catch (err: any) {
      setLoading(false);
      setError(err.message || "Failed to simulate threat");
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(0, 0, 0, 0.75)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: 20,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget && !loading) onClose();
      }}
    >
      <div
        className="card"
        style={{
          width: "100%",
          maxWidth: 620,
          background: "var(--panel)",
          border: "1px solid var(--cyan)",
          boxShadow: "0 0 30px rgba(0, 229, 255, 0.2)",
          padding: 28,
          borderRadius: 8,
          maxHeight: "90vh",
          overflowY: "auto",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 20 }}>⚡</span>
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: "var(--ink)" }}>
              Live Threat Injection & Detection Simulator
            </h2>
          </div>
          {!loading && (
            <button
              onClick={onClose}
              style={{
                background: "transparent",
                border: "none",
                color: "var(--muted)",
                fontSize: 20,
                cursor: "pointer",
              }}
            >
              ✕
            </button>
          )}
        </div>

        <p style={{ margin: "0 0 20px 0", fontSize: 13, color: "var(--muted)", lineHeight: 1.5 }}>
          Simulate suspicious activity under <strong>your own name</strong> or custom persona. The backend will inject
          baseline + attack events into CERT logs, run the dual-baseline and CUSUM drift detection models live, and flag
          the account in real-time.
        </p>

        {error && (
          <div style={{ padding: "10px 14px", background: "rgba(239, 68, 68, 0.15)", border: "1px solid var(--critical)", borderRadius: 6, color: "var(--critical)", fontSize: 12, marginBottom: 16 }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSimulate} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--muted)", marginBottom: 6 }}>
                Your Name / Persona
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                disabled={loading}
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  background: "var(--bg-subtle)",
                  border: "1px solid var(--line)",
                  borderRadius: 6,
                  color: "var(--ink)",
                  fontSize: 13,
                }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 500, color: "var(--muted)", marginBottom: 6 }}>
                Role in Organization
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                disabled={loading}
                style={{
                  width: "100%",
                  padding: "9px 12px",
                  background: "var(--bg-subtle)",
                  border: "1px solid var(--line)",
                  borderRadius: 6,
                  color: "var(--ink)",
                  fontSize: 13,
                }}
              >
                <option value="Engineer">Senior Engineer</option>
                <option value="Administrator">System Administrator (Privileged)</option>
                <option value="Accountant">Corporate Accountant</option>
                <option value="Financial Controller">Financial Controller (Small Cohort)</option>
              </select>
            </div>
          </div>

          <div style={{ padding: 14, background: "rgba(0,0,0,0.25)", borderRadius: 6, border: "1px solid var(--line)" }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "var(--cyan)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 12 }}>
              Suspicious Behaviors to Simulate:
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={afterHours}
                  onChange={(e) => setAfterHours(e.target.checked)}
                  disabled={loading}
                />
                <span>🌙 <strong>After-Hours Access:</strong> Logon detected at 11:15 PM outside business hours</span>
              </label>

              <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={usb}
                  onChange={(e) => setUsb(e.target.checked)}
                  disabled={loading}
                />
                <span>💾 <strong>Unauthorized Device:</strong> Connect USB storage drive (R:\) to workstation</span>
              </label>

              <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, cursor: "pointer" }}>
                <input
                  type="checkbox"
                  checked={cloudUpload}
                  onChange={(e) => setCloudUpload(e.target.checked)}
                  disabled={loading}
                />
                <span>🌐 <strong>Cloud Exfiltration:</strong> High-volume upload to external file storage</span>
              </label>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
            <div>
              <label style={{ display: "block", fontSize: 11, color: "var(--muted)", marginBottom: 4 }}>
                Target Upload Site
              </label>
              <input
                type="text"
                value={site}
                onChange={(e) => setSite(e.target.value)}
                disabled={loading}
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  background: "var(--bg-subtle)",
                  border: "1px solid var(--line)",
                  borderRadius: 6,
                  color: "var(--ink)",
                  fontSize: 12,
                  fontFamily: "IBM Plex Mono",
                }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: 11, color: "var(--muted)", marginBottom: 4 }}>
                Sensitive File
              </label>
              <input
                type="text"
                value={file}
                onChange={(e) => setFile(e.target.value)}
                disabled={loading}
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  background: "var(--bg-subtle)",
                  border: "1px solid var(--line)",
                  borderRadius: 6,
                  color: "var(--ink)",
                  fontSize: 12,
                  fontFamily: "IBM Plex Mono",
                }}
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: 11, color: "var(--muted)", marginBottom: 4 }}>
                External Email Drop
              </label>
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={loading}
                style={{
                  width: "100%",
                  padding: "8px 10px",
                  background: "var(--bg-subtle)",
                  border: "1px solid var(--line)",
                  borderRadius: 6,
                  color: "var(--ink)",
                  fontSize: 12,
                  fontFamily: "IBM Plex Mono",
                }}
              />
            </div>
          </div>

          {loading ? (
            <div style={{ padding: 16, background: "rgba(0, 229, 255, 0.1)", border: "1px solid var(--cyan)", borderRadius: 6, textAlign: "center" }}>
              <div style={{ fontSize: 13, color: "var(--cyan)", fontWeight: 500, marginBottom: 6 }}>
                ⚡ Processing Live ML Detection Pipeline...
              </div>
              <div className="mono" style={{ fontSize: 12, color: "var(--ink)" }}>
                {statusMsg}
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 8 }}>
              <button
                type="button"
                onClick={onClose}
                className="btn btn-secondary"
                style={{ padding: "9px 16px", fontSize: 13 }}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                style={{
                  padding: "9px 20px",
                  fontSize: 13,
                  fontWeight: 600,
                  background: "linear-gradient(135deg, var(--cyan), #00b4d8)",
                  color: "#0a0e17",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                ⚡ Inject Activity & Run Detection
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
