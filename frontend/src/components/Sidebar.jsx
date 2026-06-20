import { useNavigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import api from "../api";

const NAV = [
  { path: "/",          label: "Tableau de Bord", icon: "⬛" },
  { path: "/vehicules", label: "Véhicules",        icon: "🚗" },
  { path: "/conducteurs",label:"Conducteurs",      icon: "🪪" },
  { path: "/pietons",   label: "Piétons",           icon: "🚶" },
  { path: "/employes",  label: "Employés",          icon: "💼" },
  { path: "/presences", label: "Présences",         icon: "📋" },
  { path: "/blacklist", label: "Liste Noire",       icon: "🚫" },
  { path: "/alertes",   label: "Alertes",           icon: "🔔", alert: true },
  { path: "/cameras",   label: "Caméras IP",        icon: "📷" },
  { path: "/rapports",  label: "Rapports",          icon: "📊" },
  { path: "/admin",     label: "Administration",    icon: "⚙️" },
];

export default function Sidebar() {
  const nav = useNavigate();
  const loc = useLocation();
  let user = {};
  try { user = JSON.parse(localStorage.getItem("user") || "{}"); } catch (_) {}
  const [alertCount, setAlertCount] = useState(0);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const fetchAlerts = () =>
      api.get("/api/alertes/stats").then(r => setAlertCount(r.data.non_traitees)).catch(() => {});
    fetchAlerts();
    const i = setInterval(fetchAlerts, 15000);
    return () => clearInterval(i);
  }, []);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    nav("/login");
  };

  return (
    <nav className="sidebar">
      <div className="sidebar-brand">
        <h2>Accès Système</h2>
        <p>Enregistrement Auto</p>
      </div>
      <div className="sidebar-nav">
        {NAV.map(({ path, label, icon, alert }) => (
          <div key={path}
            className={`nav-item ${loc.pathname === path ? "active" : ""}`}
            onClick={() => nav(path)}>
            <span>{icon}</span>
            <span>{label}</span>
            {alert && alertCount > 0 && (
              <span className="alert-badge">{alertCount}</span>
            )}
          </div>
        ))}
      </div>
      <div className="sidebar-footer">
        <div style={{ marginBottom: 8 }}>
          {now.toLocaleTimeString("fr")}<br />
          <span style={{ color: "var(--muted)" }}>{now.toLocaleDateString("fr")}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>👤 {user.username || "—"}</span>
          <button className="btn btn-outline btn-sm" onClick={logout}>Déco.</button>
        </div>
      </div>
    </nav>
  );
}
