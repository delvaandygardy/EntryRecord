import { useEffect, useState } from "react";
import api from "../api";
import toast from "react-hot-toast";

export default function Presences() {
  const [presences, setPresences] = useState([]);
  const [matricule, setMatricule] = useState("");
  const [point, setPoint] = useState("Principal");
  const [lastBadge, setLastBadge] = useState(null);

  const load = () =>
    api.get("/api/employes/presences/today").then(r => setPresences(Array.isArray(r.data) ? r.data : [])).catch(() => {});

  useEffect(() => { load(); }, []);

  const badge = async (e) => {
    e.preventDefault();
    if (!matricule.trim()) return;
    try {
      const { data } = await api.post("/api/employes/badge", { matricule: matricule.trim(), point_entree: point });
      const emp = data.employe;
      const msg = `${data.type === "ENTREE" ? "✅ ENTRÉE" : "🚪 SORTIE"} — ${emp.prenom} ${emp.nom}`;
      toast.success(msg, { duration: 5000 });
      setLastBadge({ ...data, ts: new Date().toLocaleTimeString("fr") });
      setMatricule("");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Matricule inconnu");
    }
  };

  const stats = {
    entrees: presences.filter(p => p.type === "ENTREE").length,
    sorties: presences.filter(p => p.type === "SORTIE").length,
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">📋 Présences & Badgeage</h1>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: 20 }}>
        {/* Badge scanner */}
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header">Scanner Badge</div>
            <div style={{ padding: 16 }}>
              <form onSubmit={badge}>
                <div className="form-group">
                  <label>Matricule</label>
                  <input className="form-control" style={{ fontSize: 18, fontFamily: "monospace" }}
                    value={matricule} autoFocus
                    onChange={e => setMatricule(e.target.value.toUpperCase())}
                    placeholder="EMP001" />
                  <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>
                    Scanner USB ou saisie manuelle
                  </p>
                </div>
                <div className="form-group">
                  <label>Point d'entrée</label>
                  <select className="form-select" value={point} onChange={e => setPoint(e.target.value)}>
                    <option>Principal</option>
                    <option>Entrée Nord</option>
                    <option>Entrée Sud</option>
                  </select>
                </div>
                <button type="submit" className="btn btn-primary" style={{ width: "100%" }}>
                  Badger
                </button>
              </form>
            </div>
          </div>

          {lastBadge && (
            <div className={`card`} style={{ borderLeft: `3px solid ${lastBadge.type==="ENTREE"?"var(--success)":"var(--warning)"}` }}>
              <div style={{ padding: 16 }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: lastBadge.type==="ENTREE"?"var(--success)":"var(--warning)" }}>
                  {lastBadge.type === "ENTREE" ? "✅ ENTRÉE" : "🚪 SORTIE"}
                </div>
                <div style={{ fontSize: 16, marginTop: 6 }}>
                  {lastBadge.employe?.prenom} <strong>{lastBadge.employe?.nom}</strong>
                </div>
                <div style={{ color: "var(--muted)", fontSize: 12, marginTop: 2 }}>{lastBadge.ts}</div>
              </div>
            </div>
          )}

          <div className="stat-grid" style={{ marginTop: 16 }}>
            <div className="stat-card green"><div className="num">{stats.entrees}</div><div className="lbl">Entrées auj.</div></div>
            <div className="stat-card yellow"><div className="num">{stats.sorties}</div><div className="lbl">Sorties auj.</div></div>
          </div>
        </div>

        {/* Table */}
        <div className="card">
          <div className="card-header">Journal du jour ({presences.length})</div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Matricule</th><th>Nom</th><th>Poste</th><th>Type</th><th>Heure</th></tr></thead>
              <tbody>
                {presences.map(p => (
                  <tr key={p.id}>
                    <td><code style={{ fontSize: 12 }}>{p.matricule}</code></td>
                    <td>{p.prenom} {p.nom}</td>
                    <td style={{ color: "var(--muted)", fontSize: 12 }}>{p.poste || "—"}</td>
                    <td>
                      <span className={`badge ${p.type==="ENTREE"?"badge-success":"badge-warning"}`}>
                        {p.type}
                      </span>
                    </td>
                    <td style={{ color: "var(--muted)", fontSize: 12 }}>
                      {p.timestamp?.slice(11,16)}
                    </td>
                  </tr>
                ))}
                {presences.length === 0 && <tr><td colSpan={5} className="empty">Aucun badgeage aujourd'hui</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
