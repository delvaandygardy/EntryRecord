import { useRef, useState } from "react";
import api from "../api";
import toast from "react-hot-toast";
import { usePoints } from "../hooks/usePoints";

const CATS = { employe: "Employé", conducteur: "Conducteur", pieton: "Piéton" };
const CAT_COLOR = { employe: "var(--primary)", conducteur: "var(--warning)", pieton: "#8b5cf6" };

export default function Scanner() {
  const inputRef = useRef(null);
  const points = usePoints();
  const [code, setCode] = useState("");
  const [point, setPoint] = useState("Principal");
  const [result, setResult] = useState(null);
  const [scans, setScans] = useState([]);
  const [loading, setLoading] = useState(false);

  const doScan = async (e) => {
    e?.preventDefault();
    const raw = code.trim();
    if (!raw) return;
    setLoading(true);
    try {
      const { data } = await api.post("/api/scan", { code: raw, point_entree: point });
      const entry = { ...data, ts: new Date().toLocaleTimeString("fr"), code: raw };
      setResult(entry);
      setScans(prev => [entry, ...prev].slice(0, 30));
      if (data.blacklist) toast.error("⚠️ LISTE NOIRE — Alerte créée !", { duration: 8000 });
      if (data.auto_vehicle) toast.success(`🚗 Lié au véhicule ${data.auto_vehicle.plaque}`, { duration: 5000 });
    } catch (err) {
      const msg = err.response?.data?.detail || "Code non reconnu";
      setResult({ error: msg, code: raw, ts: new Date().toLocaleTimeString("fr") });
      toast.error(msg);
    } finally {
      setCode("");
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const stats = {
    employes: scans.filter(s => s.categorie === "employe").length,
    conducteurs: scans.filter(s => s.categorie === "conducteur").length,
    pietons: scans.filter(s => s.categorie === "pieton").length,
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">📲 Scanner d'Entrée</h1>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 20 }}>
        {/* Panneau scanner */}
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-header">Scanner un badge</div>
            <div style={{ padding: 20 }}>
              <form onSubmit={doScan}>
                <div className="form-group">
                  <label style={{ fontSize: 12, color: "var(--muted)" }}>Point d'entrée</label>
                  <select className="form-select" value={point}
                    onChange={e => setPoint(e.target.value)}>
                    {points.map(p => <option key={p}>{p}</option>)}
                  </select>
                </div>
                <div className="form-group" style={{ marginTop: 12 }}>
                  <label>Code scanner / QR</label>
                  <input
                    ref={inputRef}
                    className="form-control"
                    style={{ fontSize: 20, fontFamily: "monospace", textAlign: "center", letterSpacing: 2 }}
                    value={code}
                    autoFocus
                    autoComplete="off"
                    placeholder="Scanner ou saisir…"
                    onChange={e => setCode(e.target.value.toUpperCase())}
                  />
                  <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 6 }}>
                    Branchez un scanner USB — il écrit ici automatiquement
                  </p>
                </div>
                <button type="submit" className="btn btn-primary"
                  style={{ width: "100%", fontSize: 16 }} disabled={loading || !code.trim()}>
                  {loading ? "Traitement…" : "Enregistrer"}
                </button>
              </form>
            </div>
          </div>

          {/* Résultat dernier scan */}
          {result && (
            <div className="card" style={{
              borderLeft: `4px solid ${result.error ? "var(--danger)" : result.blacklist ? "var(--danger)" : "var(--success)"}`,
              marginBottom: 16,
            }}>
              <div style={{ padding: 16 }}>
                {result.error ? (
                  <>
                    <div style={{ fontSize: 22, fontWeight: 700, color: "var(--danger)" }}>✗ Erreur</div>
                    <div style={{ color: "var(--danger)", marginTop: 4 }}>{result.error}</div>
                    <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>{result.code}</div>
                  </>
                ) : (
                  <>
                    <div style={{ fontSize: 22, fontWeight: 700, color: result.blacklist ? "var(--danger)" : result.type === "ENTREE" ? "var(--success)" : "var(--warning)" }}>
                      {result.blacklist ? "⚠️ LISTE NOIRE" : result.type === "ENTREE" ? "✅ ENTRÉE" : "🚪 SORTIE"}
                    </div>
                    <div style={{ fontSize: 17, marginTop: 6 }}>
                      {result.personne?.prenom} <strong>{result.personne?.nom}</strong>
                    </div>
                    <div style={{ fontSize: 12, color: CAT_COLOR[result.categorie], marginTop: 2 }}>
                      {CATS[result.categorie]} · <code>{result.personne?.ref}</code>
                    </div>
                    {result.personne?.poste && (
                      <div style={{ fontSize: 12, color: "var(--muted)" }}>{result.personne.poste}</div>
                    )}
                    {result.auto_vehicle && (
                      <div style={{ fontSize: 12, color: "#3fb950", marginTop: 4 }}>
                        🚗 Lié automatiquement au véhicule <strong>{result.auto_vehicle.plaque}</strong>
                      </div>
                    )}
                    <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 4 }}>{result.ts}</div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Stats session */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
            <div className="card" style={{ padding: "10px 8px", textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: "var(--primary)" }}>{stats.employes}</div>
              <div style={{ fontSize: 11, color: "var(--muted)" }}>Employés</div>
            </div>
            <div className="card" style={{ padding: "10px 8px", textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: "var(--warning)" }}>{stats.conducteurs}</div>
              <div style={{ fontSize: 11, color: "var(--muted)" }}>Conducteurs</div>
            </div>
            <div className="card" style={{ padding: "10px 8px", textAlign: "center" }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#8b5cf6" }}>{stats.pietons}</div>
              <div style={{ fontSize: 11, color: "var(--muted)" }}>Piétons</div>
            </div>
          </div>
        </div>

        {/* Journal de session */}
        <div className="card">
          <div className="card-header">Journal de session ({scans.length})</div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Heure</th>
                  <th>Catégorie</th>
                  <th>Nom</th>
                  <th>Référence</th>
                  <th>Type</th>
                  <th>Point</th>
                </tr>
              </thead>
              <tbody>
                {scans.map((s, i) => (
                  <tr key={i} style={{ opacity: s.error ? 0.5 : 1 }}>
                    <td style={{ color: "var(--muted)", fontSize: 12 }}>{s.ts}</td>
                    <td>
                      {s.error ? (
                        <span className="badge badge-danger">Erreur</span>
                      ) : (
                        <span className="badge" style={{ background: CAT_COLOR[s.categorie] + "22", color: CAT_COLOR[s.categorie] }}>
                          {CATS[s.categorie]}
                        </span>
                      )}
                    </td>
                    <td>
                      {s.error ? <span style={{ color: "var(--danger)", fontSize: 12 }}>{s.error}</span>
                        : <>{s.personne?.prenom} <strong>{s.personne?.nom}</strong></>}
                    </td>
                    <td><code style={{ fontSize: 11 }}>{s.personne?.ref || s.code}</code></td>
                    <td>
                      {!s.error && (
                        <span className={`badge ${s.blacklist ? "badge-danger" : s.type === "ENTREE" ? "badge-success" : "badge-warning"}`}>
                          {s.blacklist ? "⚠️ BL" : s.type}
                        </span>
                      )}
                    </td>
                    <td style={{ fontSize: 12, color: "var(--muted)" }}>{s.point_entree || point}</td>
                  </tr>
                ))}
                {scans.length === 0 && (
                  <tr><td colSpan={6} className="empty">Aucun scan cette session</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
