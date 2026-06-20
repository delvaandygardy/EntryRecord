import { useEffect, useState } from "react";
import api from "../api";
import toast from "react-hot-toast";

const BLANK = { username:"", email:"", password:"", nom:"", prenom:"", role_id:3 };

export default function Admin() {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [form, setForm] = useState(BLANK);
  const [editId, setEditId] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const load = () => {
    api.get("/api/admin/utilisateurs").then(r => setUsers(Array.isArray(r.data) ? r.data : [])).catch(() => {});
    api.get("/api/admin/roles").then(r => setRoles(Array.isArray(r.data) ? r.data : [])).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const openEdit = (u) => { setForm({...u, password:""}); setEditId(u.id); setShowForm(true); };
  const openAdd  = () => { setForm(BLANK); setEditId(null); setShowForm(true); };

  const save = async (e) => {
    e.preventDefault();
    try {
      if (editId) { await api.put(`/api/admin/utilisateurs/${editId}`, form); toast.success("Modifié"); }
      else        { await api.post("/api/admin/utilisateurs", form); toast.success("Utilisateur créé"); }
      setShowForm(false); load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erreur"); }
  };

  const del = async (id) => {
    if (!confirm("Supprimer cet utilisateur ?")) return;
    await api.delete(`/api/admin/utilisateurs/${id}`); load();
  };

  const roleLabel = (id) => roles.find(r => r.id === id)?.nom || id;
  const roleBadge = (nom) => ({ admin:"badge-danger", superviseur:"badge-warning", operateur:"badge-primary", lecteur:"badge-muted" }[nom] || "badge-muted");

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">⚙️ Administration</h1>
        <button className="btn btn-primary btn-sm" onClick={openAdd}>+ Nouvel utilisateur</button>
      </div>

      <div className="alert alert-warning" style={{ marginBottom: 16 }}>
        ⚠️ Section réservée aux administrateurs. Les modifications prennent effet immédiatement.
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>{editId ? "Modifier utilisateur" : "Créer utilisateur"}</h3>
            <form onSubmit={save}>
              <div className="form-row">
                <div className="form-group"><label>Nom d'utilisateur *</label>
                  <input className="form-control" required value={form.username||""}
                    onChange={e => setForm({...form,username:e.target.value})} /></div>
                <div className="form-group"><label>Email</label>
                  <input className="form-control" type="email" value={form.email||""}
                    onChange={e => setForm({...form,email:e.target.value})} /></div>
                <div className="form-group"><label>{editId ? "Nouveau mot de passe" : "Mot de passe *"}</label>
                  <input className="form-control" type="password" required={!editId} value={form.password||""}
                    onChange={e => setForm({...form,password:e.target.value})} /></div>
                <div className="form-group"><label>Nom</label>
                  <input className="form-control" value={form.nom||""}
                    onChange={e => setForm({...form,nom:e.target.value})} /></div>
                <div className="form-group"><label>Prénom</label>
                  <input className="form-control" value={form.prenom||""}
                    onChange={e => setForm({...form,prenom:e.target.value})} /></div>
                <div className="form-group"><label>Rôle</label>
                  <select className="form-select" value={form.role_id||3}
                    onChange={e => setForm({...form,role_id:parseInt(e.target.value)})}>
                    {roles.map(r => <option key={r.id} value={r.id}>{r.nom}</option>)}
                  </select></div>
              </div>
              <div style={{ display:"flex", gap:8, justifyContent:"flex-end", marginTop:12 }}>
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
            <thead><tr><th>Utilisateur</th><th>Nom</th><th>Email</th><th>Rôle</th><th>Statut</th><th>Dernière connexion</th><th></th></tr></thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td><strong>{u.username}</strong></td>
                  <td>{u.prenom} {u.nom}</td>
                  <td style={{ color:"var(--muted)", fontSize:12 }}>{u.email||"—"}</td>
                  <td><span className={`badge ${roleBadge(u.role_nom)}`}>{u.role_nom}</span></td>
                  <td><span className={`badge ${u.actif?"badge-success":"badge-muted"}`}>{u.actif?"Actif":"Inactif"}</span></td>
                  <td style={{ color:"var(--muted)", fontSize:12 }}>{u.derniere_connexion?.slice(0,16)||"—"}</td>
                  <td style={{ display:"flex", gap:4 }}>
                    <button className="btn btn-icon btn-sm" onClick={() => openEdit(u)}>✏️</button>
                    <button className="btn btn-icon btn-sm" onClick={() => del(u.id)}>🗑</button>
                  </td>
                </tr>
              ))}
              {users.length===0 && <tr><td colSpan={7} className="empty">Aucun utilisateur</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
