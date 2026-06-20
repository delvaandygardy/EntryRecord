import { useEffect, useState } from "react";
import api from "../api";
import toast from "react-hot-toast";

const BLANK = { nom:"", prenom:"", numero_document:"", type_document:"CNI", date_naissance:"", nationalite:"HTI", date_expiration:"", point_entree:"Principal" };

export default function Personnes({ mode }) {
  const isConducteur = mode === "conducteur";
  const title = isConducteur ? "🪪 Conducteurs" : "🚶 Piétons";
  const endpoint = isConducteur ? "/api/conducteurs" : "/api/pietons";

  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [form, setForm] = useState(BLANK);
  const [showForm, setShowForm] = useState(false);

  const load = () => api.get(`${endpoint}?q=${q}&limit=300`).then(r => setRows(Array.isArray(r.data) ? r.data : [])).catch(() => {});
  useEffect(() => { load(); }, [q, mode]);

  const save = async (e) => {
    e.preventDefault();
    try {
      const { data } = await api.post(endpoint, form);
      if (data.blacklist) toast.error(`⚠️ Document ${form.numero_document} en liste noire !`);
      else toast.success("Enregistré");
      setShowForm(false);
      setForm(BLANK);
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erreur"); }
  };

  const del = async (id) => {
    if (!confirm("Supprimer ?")) return;
    await api.delete(`${endpoint}/${id}`); load();
  };

  const docTypes = isConducteur
    ? ["PERMIS","CNI","PASSEPORT"]
    : ["CNI","PASSEPORT","TITRE_SEJOUR","AUTRE"];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">{title}</h1>
        <button className="btn btn-success btn-sm" onClick={() => setShowForm(true)}>+ Ajouter</button>
      </div>

      <div className="toolbar">
        <input className="form-control" style={{ maxWidth:300 }} placeholder="Rechercher nom, document…"
          value={q} onChange={e => setQ(e.target.value)} />
        <span style={{ color:"var(--muted)", fontSize:12 }}>{rows.length} résultat(s)</span>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Enregistrer {isConducteur ? "un conducteur" : "un piéton"}</h3>
            <form onSubmit={save}>
              <div className="form-row">
                <div className="form-group"><label>Nom</label>
                  <input className="form-control" value={form.nom} onChange={e => setForm({...form,nom:e.target.value})} /></div>
                <div className="form-group"><label>Prénom</label>
                  <input className="form-control" value={form.prenom} onChange={e => setForm({...form,prenom:e.target.value})} /></div>
                <div className="form-group"><label>N° Document</label>
                  <input className="form-control" value={form.numero_document} onChange={e => setForm({...form,numero_document:e.target.value})} /></div>
                <div className="form-group"><label>Type</label>
                  <select className="form-select" value={form.type_document} onChange={e => setForm({...form,type_document:e.target.value})}>
                    {docTypes.map(t => <option key={t}>{t}</option>)}
                  </select></div>
                <div className="form-group"><label>Date naissance</label>
                  <input className="form-control" value={form.date_naissance} onChange={e => setForm({...form,date_naissance:e.target.value})} /></div>
                <div className="form-group"><label>Nationalité</label>
                  <input className="form-control" value={form.nationalite} onChange={e => setForm({...form,nationalite:e.target.value})} /></div>
                <div className="form-group"><label>Expiration</label>
                  <input className="form-control" value={form.date_expiration} onChange={e => setForm({...form,date_expiration:e.target.value})} /></div>
                <div className="form-group"><label>Point d'entrée</label>
                  <select className="form-select" value={form.point_entree} onChange={e => setForm({...form,point_entree:e.target.value})}>
                    <option>Principal</option><option>Entrée Nord</option><option>Entrée Sud</option>
                  </select></div>
              </div>
              <div style={{ display:"flex", gap:8, justifyContent:"flex-end", marginTop:8 }}>
                <button type="button" className="btn btn-outline" onClick={() => setShowForm(false)}>Annuler</button>
                <button type="submit" className="btn btn-primary">Enregistrer</button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Nom</th><th>N° Document</th><th>Type</th><th>Naissance</th><th>Nationalité</th><th>Entrée</th><th>Date/Heure</th><th></th></tr></thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.id}>
                  <td>{r.prenom} <strong>{r.nom}</strong></td>
                  <td><code style={{fontSize:12}}>{r.numero_document||"—"}</code></td>
                  <td><span className="badge badge-muted">{r.type_document}</span></td>
                  <td style={{ color:"var(--muted)", fontSize:12 }}>{r.date_naissance||"—"}</td>
                  <td style={{ color:"var(--muted)" }}>{r.nationalite||"—"}</td>
                  <td>{r.point_entree}</td>
                  <td style={{ color:"var(--muted)", fontSize:12 }}>{r.timestamp?.slice(0,16)}</td>
                  <td><button className="btn btn-icon btn-sm" onClick={() => del(r.id)}>🗑</button></td>
                </tr>
              ))}
              {rows.length===0 && <tr><td colSpan={8} className="empty">Aucun enregistrement</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
