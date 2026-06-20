import { useEffect, useState } from "react";
import api from "../api";
import toast from "react-hot-toast";

export default function Blacklist() {
  const [plaques, setPlaques] = useState([]);
  const [personnes, setPersonnes] = useState([]);
  const [tab, setTab] = useState("plaques");
  const [form, setForm] = useState({ plaque: "", motif: "", severite: "HAUTE" });
  const [formP, setFormP] = useState({ numero_document: "", nom: "", prenom: "", motif: "", severite: "HAUTE" });
  const [showForm, setShowForm] = useState(false);

  const load = () => {
    api.get("/api/blacklist/plaques").then(r => setPlaques(Array.isArray(r.data) ? r.data : [])).catch(() => {});
    api.get("/api/blacklist/personnes").then(r => setPersonnes(Array.isArray(r.data) ? r.data : [])).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const addPlaque = async (e) => {
    e.preventDefault();
    try {
      await api.post("/api/blacklist/plaques", form);
      toast.success("Plaque ajoutée à la liste noire");
      setShowForm(false);
      setForm({ plaque: "", motif: "", severite: "HAUTE" });
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erreur"); }
  };

  const addPersonne = async (e) => {
    e.preventDefault();
    try {
      await api.post("/api/blacklist/personnes", formP);
      toast.success("Personne ajoutée à la liste noire");
      setShowForm(false);
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erreur"); }
  };

  const removePlaque = async (id) => {
    if (!confirm("Retirer de la liste noire ?")) return;
    await api.delete(`/api/blacklist/plaques/${id}`);
    toast.success("Retiré");
    load();
  };

  const removePersonne = async (id) => {
    if (!confirm("Retirer de la liste noire ?")) return;
    await api.delete(`/api/blacklist/personnes/${id}`);
    toast.success("Retiré");
    load();
  };

  const sevBadge = (s) => s === "CRITIQUE" ? "badge-danger" : s === "HAUTE" ? "badge-warning" : "badge-muted";

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">🚫 Liste Noire</h1>
        <button className="btn btn-danger btn-sm" onClick={() => setShowForm(true)}>+ Ajouter</button>
      </div>

      <div style={{ display:"flex", gap:8, marginBottom:16 }}>
        <button className={`btn ${tab==="plaques"?"btn-primary":"btn-outline"}`} onClick={() => setTab("plaques")}>
          Plaques ({plaques.filter(p=>p.actif).length})
        </button>
        <button className={`btn ${tab==="personnes"?"btn-primary":"btn-outline"}`} onClick={() => setTab("personnes")}>
          Personnes ({personnes.filter(p=>p.actif).length})
        </button>
      </div>

      {showForm && tab === "plaques" && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>🚫 Ajouter une plaque à la liste noire</h3>
            <form onSubmit={addPlaque}>
              <div className="form-group"><label>Plaque *</label>
                <input className="form-control" required value={form.plaque}
                  onChange={e => setForm({...form, plaque: e.target.value.toUpperCase()})} /></div>
              <div className="form-group"><label>Motif</label>
                <input className="form-control" value={form.motif}
                  onChange={e => setForm({...form, motif: e.target.value})} /></div>
              <div className="form-group"><label>Sévérité</label>
                <select className="form-select" value={form.severite}
                  onChange={e => setForm({...form, severite: e.target.value})}>
                  <option>HAUTE</option><option>CRITIQUE</option><option>MOYENNE</option>
                </select></div>
              <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
                <button type="button" className="btn btn-outline" onClick={() => setShowForm(false)}>Annuler</button>
                <button type="submit" className="btn btn-danger">Ajouter</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showForm && tab === "personnes" && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>🚫 Ajouter une personne à la liste noire</h3>
            <form onSubmit={addPersonne}>
              <div className="form-row">
                <div className="form-group"><label>N° Document *</label>
                  <input className="form-control" required value={formP.numero_document}
                    onChange={e => setFormP({...formP, numero_document: e.target.value})} /></div>
                <div className="form-group"><label>Nom</label>
                  <input className="form-control" value={formP.nom}
                    onChange={e => setFormP({...formP, nom: e.target.value})} /></div>
                <div className="form-group"><label>Prénom</label>
                  <input className="form-control" value={formP.prenom}
                    onChange={e => setFormP({...formP, prenom: e.target.value})} /></div>
              </div>
              <div className="form-group"><label>Motif</label>
                <input className="form-control" value={formP.motif}
                  onChange={e => setFormP({...formP, motif: e.target.value})} /></div>
              <div className="form-group"><label>Sévérité</label>
                <select className="form-select" value={formP.severite}
                  onChange={e => setFormP({...formP, severite: e.target.value})}>
                  <option>HAUTE</option><option>CRITIQUE</option><option>MOYENNE</option>
                </select></div>
              <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
                <button type="button" className="btn btn-outline" onClick={() => setShowForm(false)}>Annuler</button>
                <button type="submit" className="btn btn-danger">Ajouter</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div className="table-wrap">
          {tab === "plaques" ? (
            <table>
              <thead><tr><th>Plaque</th><th>Motif</th><th>Sévérité</th><th>Statut</th><th>Ajouté le</th><th></th></tr></thead>
              <tbody>
                {plaques.map(p => (
                  <tr key={p.id} style={{ opacity: p.actif ? 1 : 0.4 }}>
                    <td><span className="badge badge-primary">{p.plaque}</span></td>
                    <td>{p.motif || "—"}</td>
                    <td><span className={`badge ${sevBadge(p.severite)}`}>{p.severite}</span></td>
                    <td><span className={`badge ${p.actif?"badge-danger":"badge-muted"}`}>{p.actif?"Actif":"Retiré"}</span></td>
                    <td style={{ color:"var(--muted)", fontSize:12 }}>{p.timestamp?.slice(0,10)}</td>
                    <td>{p.actif && <button className="btn btn-icon btn-sm" onClick={() => removePlaque(p.id)}>✕</button>}</td>
                  </tr>
                ))}
                {plaques.length === 0 && <tr><td colSpan={6} className="empty">Aucune plaque en liste noire</td></tr>}
              </tbody>
            </table>
          ) : (
            <table>
              <thead><tr><th>N° Document</th><th>Nom</th><th>Motif</th><th>Sévérité</th><th>Statut</th><th></th></tr></thead>
              <tbody>
                {personnes.map(p => (
                  <tr key={p.id} style={{ opacity: p.actif ? 1 : 0.4 }}>
                    <td><code style={{fontSize:12}}>{p.numero_document}</code></td>
                    <td>{p.prenom} {p.nom}</td>
                    <td>{p.motif || "—"}</td>
                    <td><span className={`badge ${sevBadge(p.severite)}`}>{p.severite}</span></td>
                    <td><span className={`badge ${p.actif?"badge-danger":"badge-muted"}`}>{p.actif?"Actif":"Retiré"}</span></td>
                    <td>{p.actif && <button className="btn btn-icon btn-sm" onClick={() => removePersonne(p.id)}>✕</button>}</td>
                  </tr>
                ))}
                {personnes.length === 0 && <tr><td colSpan={6} className="empty">Aucune personne en liste noire</td></tr>}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
