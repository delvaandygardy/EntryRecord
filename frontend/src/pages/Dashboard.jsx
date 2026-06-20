import { useEffect, useRef, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import api from "../api";

function LivePulse() {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
      <span style={{
        width: 8, height: 8, borderRadius: "50%", background: "#3fb950",
        animation: "pulse 1.5s infinite", display: "inline-block"
      }} />
      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}`}</style>
      <span style={{ fontSize: 11, color: "#3fb950" }}>LIVE</span>
    </span>
  );
}

function ConfBar({ val }) {
  const pct = Math.round((val || 0) * 100);
  const color = pct > 80 ? "#238636" : pct > 50 ? "#9e6a03" : "#b62324";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ flex: 1, height: 5, background: "#30363d", borderRadius: 3 }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 3, transition: "width .3s" }} />
      </div>
      <span style={{ fontSize: 11, color, minWidth: 28 }}>{pct}%</span>
    </div>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState({});
  const [recent, setRecent] = useState({ vehicules: [], presences: [] });
  const [alertes, setAlertes] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [liveVehicules, setLiveVehicules] = useState([]);
  const prevIds = useRef(new Set());

  const loadVehicules = () =>
    api.get("/api/vehicules?limit=10").then(r => {
      const rows = Array.isArray(r.data) ? r.data : [];
      const newOnes = rows.filter(v => !prevIds.current.has(v.id));
      if (newOnes.length > 0) {
        newOnes.forEach(v => prevIds.current.add(v.id));
        setLiveVehicules(prev => [...newOnes, ...prev].slice(0, 20));
      }
      if (prevIds.current.size === 0) {
        rows.forEach(v => prevIds.current.add(v.id));
        setLiveVehicules(rows);
      }
      setRecent(p => ({ ...p, vehicules: rows.slice(0, 8) }));
    }).catch(() => {});

  useEffect(() => {
    const loadAll = () => {
      api.get("/api/reports/stats").then(r => setStats(r.data || {})).catch(() => {});
      api.get("/api/alertes?traitee=false&limit=5").then(r => setAlertes(Array.isArray(r.data) ? r.data : [])).catch(() => {});
      api.get("/api/cameras").then(r => setCameras(Array.isArray(r.data) ? r.data : [])).catch(() => {});
      loadVehicules();
    };
    loadAll();
    const slow = setInterval(() => {
      api.get("/api/reports/stats").then(r => setStats(r.data || {})).catch(() => {});
      api.get("/api/alertes?traitee=false&limit=5").then(r => setAlertes(Array.isArray(r.data) ? r.data : [])).catch(() => {});
      api.get("/api/cameras").then(r => setCameras(Array.isArray(r.data) ? r.data : [])).catch(() => {});
    }, 10000);
    const fast = setInterval(loadVehicules, 4000);
    return () => { clearInterval(slow); clearInterval(fast); };
  }, []);

  const cards = [
    { key: "vehicules_today",   label: "Véhicules auj.",   cls: "blue",   icon: "🚗" },
    { key: "conducteurs_today", label: "Conducteurs auj.", cls: "green",  icon: "🪪" },
    { key: "pietons_today",     label: "Piétons auj.",     cls: "yellow", icon: "🚶" },
    { key: "alertes_actives",   label: "Alertes actives",  cls: "red",    icon: "🔔" },
    { key: "employes_actifs",   label: "Employés actifs",  cls: "green",  icon: "💼" },
    { key: "presences_today",   label: "Présences auj.",   cls: "blue",   icon: "📋" },
    { key: "vehicules_total",   label: "Total véhicules",  cls: "yellow", icon: "🏷️" },
    { key: "cameras_actives",   label: "Caméras actives",  cls: "red",    icon: "📷" },
  ];

  const chartData = [
    { name: "Véh.",  val: stats.vehicules_today   || 0 },
    { name: "Cond.", val: stats.conducteurs_today  || 0 },
    { name: "Pié.",  val: stats.pietons_today      || 0 },
    { name: "Prés.", val: stats.presences_today    || 0 },
    { name: "Alert.", val: stats.alertes_actives   || 0 },
  ];

  const camActives = cameras.filter(c => c.streaming).length;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">⬛ Tableau de Bord</h1>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <LivePulse />
          <span style={{ color: "var(--muted)", fontSize: 12 }}>Véhicules: 4s • Autres: 10s</span>
        </div>
      </div>

      <div className="stat-grid">
        {cards.map(({ key, label, cls, icon }) => (
          <div key={key} className={`stat-card ${cls}`}>
            <div className="num">{key === "cameras_actives" ? camActives : (stats[key] ?? "—")}</div>
            <div className="lbl">{label}</div>
            <div className="icon">{icon}</div>
          </div>
        ))}
      </div>

      {/* Cameras status */}
      {cameras.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-header">
            📷 Statut des caméras
            <a href="/cameras" style={{ fontSize: 12, color: "var(--primary)" }}>Gérer</a>
          </div>
          <div style={{ padding: "8px 16px 16px", display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 10 }}>
            {cameras.map(cam => (
              <div key={cam.id} style={{
                padding: "10px 14px", borderRadius: 8,
                border: `1px solid ${cam.streaming ? "#238636" : "#30363d"}`,
                background: cam.streaming ? "rgba(35,134,54,.08)" : "var(--surface2)"
              }}>
                <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{cam.nom}</div>
                <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 6 }}>{cam.point_entree}</div>
                <span style={{
                  fontSize: 11, padding: "2px 8px", borderRadius: 4,
                  background: cam.streaming ? "#238636" : "#30363d",
                  color: "#fff"
                }}>
                  {cam.streaming ? "🟢 ANPR actif" : "⚫ Inactif"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        {/* Chart */}
        <div className="card">
          <div className="card-header">Activité du jour</div>
          <div style={{ padding: 16 }}>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30363d" />
                <XAxis dataKey="name" tick={{ fill: "#8b949e", fontSize: 12 }} />
                <YAxis tick={{ fill: "#8b949e", fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #30363d", color: "#c9d1d9" }} />
                <Bar dataKey="val" fill="#1a73e8" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Alerts */}
        <div className="card">
          <div className="card-header">
            🔔 Alertes récentes
            <a href="/alertes" style={{ fontSize: 12, color: "var(--primary)" }}>Voir tout</a>
          </div>
          <div className="table-wrap">
            {alertes.length === 0
              ? <div className="empty">Aucune alerte active</div>
              : <table><tbody>
                  {alertes.map(a => (
                    <tr key={a.id}>
                      <td><span className="badge badge-danger">{a.type}</span></td>
                      <td style={{ maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.message}</td>
                      <td style={{ color: "var(--muted)", fontSize: 11 }}>{a.timestamp?.slice(0, 16)}</td>
                    </tr>
                  ))}
                </tbody></table>
            }
          </div>
        </div>
      </div>

      {/* Live ANPR detections */}
      <div className="card">
        <div className="card-header">
          <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
            🚗 Détections ANPR en direct <LivePulse />
          </span>
          <a href="/vehicules" style={{ fontSize: 12, color: "var(--primary)" }}>Voir tout</a>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Plaque</th>
                <th>Confiance</th>
                <th>Point d'entrée</th>
                <th>Notes</th>
                <th>Date / Heure</th>
              </tr>
            </thead>
            <tbody>
              {liveVehicules.map((v, i) => (
                <tr key={v.id} style={{ opacity: i === 0 ? 1 : Math.max(0.5, 1 - i * 0.05) }}>
                  <td>
                    <span className="badge badge-primary" style={{ fontFamily: "monospace", letterSpacing: 2 }}>
                      {v.plaque}
                    </span>
                  </td>
                  <td style={{ minWidth: 90 }}>
                    <ConfBar val={v.confidence} />
                  </td>
                  <td>{v.point_entree}</td>
                  <td style={{ color: "var(--muted)", fontSize: 12 }}>{v.notes || "—"}</td>
                  <td style={{ color: "var(--muted)", fontSize: 12, whiteSpace: "nowrap" }}>
                    {v.timestamp?.slice(0, 16)}
                  </td>
                </tr>
              ))}
              {liveVehicules.length === 0 && (
                <tr><td colSpan={5} className="empty">En attente de détections…</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
