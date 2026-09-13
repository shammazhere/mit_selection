import { NavLink, Route, Routes } from "react-router-dom";
import CasePage from "./pages/CasePage";
import QueuePage from "./pages/QueuePage";

export default function App() {
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
        <nav style={{ display: "flex", gap: 20, fontSize: 13, fontWeight: 500 }}>
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
        </nav>
      </header>
      <div style={{ overflowY: "auto" }}>
        <Routes>
          <Route path="/" element={<QueuePage />} />
          <Route path="/case/:userId" element={<CasePage />} />
        </Routes>
      </div>
    </div>
  );
}
