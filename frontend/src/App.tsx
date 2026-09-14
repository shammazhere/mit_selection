import { useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import CasePage from "./pages/CasePage";
import QueuePage from "./pages/QueuePage";
import ThreatSimulatorModal from "./components/ThreatSimulatorModal";
import LiveDeviceSensorModal from "./components/LiveDeviceSensorModal";

export default function App() {
  const [isSimOpen, setIsSimOpen] = useState(false);
  const [isDeviceSensorOpen, setIsDeviceSensorOpen] = useState(false);
  const isSensorActive = typeof window !== "undefined" && localStorage.getItem("silent_shift_sensor_active") === "true";

  return (
    <div style={{ minHeight: "100vh", display: "grid", gridTemplateRows: "56px 1fr" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 32px",
          borderBottom: "1px solid var(--line)",
          background: "var(--bg-subtle)",
          backdropFilter: "blur(12px)",
        }}
      >
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "var(--cyan)",
              boxShadow: "0 0 8px var(--cyan)",
            }}
          />
          <strong style={{ letterSpacing: "0.12em", fontSize: 14 }}>SILENT SHIFT</strong>
          <span
            className="mono"
            style={{
              color: "var(--muted)",
              fontSize: 11,
              background: "var(--panel)",
              padding: "2px 8px",
              borderRadius: 4,
              border: "1px solid var(--line)",
            }}
          >
            Investigator Console
          </span>
        </div>
        <nav style={{ display: "flex", gap: 16, alignItems: "center", fontSize: 13, fontWeight: 500 }}>
          <NavLink
            to="/"
            end
            style={({ isActive }) => ({
              color: isActive ? "var(--cyan)" : "var(--muted)",
              borderBottom: isActive ? "2px solid var(--cyan)" : "2px solid transparent",
              padding: "16px 0",
              transition: "color 0.2s, border-color 0.2s",
            })}
          >
            Risk Queue
          </NavLink>
          <button
            onClick={() => setIsDeviceSensorOpen(true)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: isSensorActive ? "rgba(82, 183, 136, 0.15)" : "var(--panel)",
              border: isSensorActive ? "1px solid rgba(82, 183, 136, 0.4)" : "1px solid var(--line)",
              color: isSensorActive ? "var(--low)" : "var(--text)",
              padding: "6px 14px",
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s",
            }}
          >
            <span>📡</span> {isSensorActive ? "Device Sensor: Active" : "Connect My Device"}
          </button>
          <button
            onClick={() => setIsSimOpen(true)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "rgba(0, 229, 255, 0.12)",
              border: "1px solid rgba(0, 229, 255, 0.4)",
              color: "var(--cyan)",
              padding: "6px 14px",
              borderRadius: 6,
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s",
            }}
          >
            <span>⚡</span> Threat Simulator
          </button>
        </nav>
      </header>
      <div style={{ overflowY: "auto" }}>
        <Routes>
          <Route path="/" element={<QueuePage />} />
          <Route path="/case/:userId" element={<CasePage />} />
        </Routes>
      </div>
      <ThreatSimulatorModal isOpen={isSimOpen} onClose={() => setIsSimOpen(false)} />
      <LiveDeviceSensorModal isOpen={isDeviceSensorOpen} onClose={() => setIsDeviceSensorOpen(false)} />
    </div>
  );
}
