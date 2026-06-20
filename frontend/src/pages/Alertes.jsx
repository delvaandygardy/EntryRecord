import { useEffect, useState } from "react";
import api from "../api";
import toast from "react-hot-toast";

export default function Alertes() {
  const [alertes, setAlertes] = useState([]);
  const [showTraitees, setShowTraitees] = useState(false);
  const [stats, setStats] = useState({});

  const load = () => {
    api.get(`/api/alertes?traitee=${showTraitees}&limit=200`).then(r => setAlertes(Array.isArray(r.data) ? r.data : [])).catch(() => {});
    api.get("/api/alertes/stats").then(r => setStats(r.data || {})).catch(() => {});
  };
  useEffect(() => { load(); }, [showTraitees]);

  // WebSocket for real-time
  useEffect(() => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/alertes`);
    ws.onmessage = () => load();
    return () => ws.close();
  }, []);

  const traiter = async (id) => {
    await api.patch(`/api/alertes/${id}`, { traitee: true });
    toast.success("Alerte traitée");
    load();
  };

  const del = async (id) => {
    await api.delete(`/api/alertes/${id}`);
    load();
  };

  const sevClass = (s) => s === "CRITIQUE" ? "badge-danger" : s === "HAUTE" ? "badge-warning" : "badge-muted";

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">🔔 Alertes</h1>
        <button className="btn btn-outline btn-sm" onClick={() => setShowTraitees(!showTraitees)}>
          {showTraitees ? "Voir actives" : "Voir traitées"}
        </button>
      </div>

      <div className="stat-grid" style={{ marginBottom: 20 }}>
        <div className="stat-card red"><div className="num">{stats.non_traitees || 0}</div><div className="lbl">Non traitées</div></div>
        <div className="stat-card yellow"><div className="num">{stats.critiques || 0}</div><div className="lbl">Critiques</div></div>
        <div className="stat-card blue"><div className="num">{stats.aujourd_hui || 0}</div><div className="lbl">Aujourd'hui</div></div>
      </div>

      {!showTraitees && stats.non_traitees > 0 && (
        <div className="alert alert-danger">
          ⚠️ {stats.non_traitees} alerte(s) active(s) requièrent votre attention
        </div>
      )}

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Type</th><th>Message</th><th>Référence</th><th>Sévérité</th><th>Date/Heure</th><th>Actions</th></tr>
            </thead>
            <tbody>
              {alertes.map(a => (
                <tr key={a.id}>
                  <td><span className="badge badge-danger">{a.type}</span></td>
                  <td style={{ maxWidth: 280, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
                    {a.message || "—"}
                  </td>
                  <td><code style={{ fontSize:12 }}>{a.reference || "—"}</code></td>
                  <td><span className={`badge ${sevClass(a.severite)}`}>{a.severite}</span></td>
                  <td style={{ color:"var(--muted)", fontSize:12 }}>{a.timestamp?.slice(0,16)}</td>
                  <td style={{ display:"flex", gap:4 }}>
                    {!a.traitee && (
                      <button className="btn btn-success btn-sm" onClick={() => traiter(a.id)}>✓ Traiter</button>
                    )}
                    <button className="btn btn-icon btn-sm" onClick={() => del(a.id)}>🗑</button>
                  </td>
                </tr>
              ))}
              {alertes.length === 0 && <tr><td colSpan={6} className="empty">Aucune alerte</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
