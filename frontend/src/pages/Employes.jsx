import { useEffect, useState } from "react";
import api from "../api";
import toast from "react-hot-toast";

function QRModal({ emp, onClose }) {
  const [src, setSrc] = useState(null);
  useEffect(() => {
    api.get(`/api/qr/employe/${emp.id}`, { responseType: "blob" })
      .then(r => setSrc(URL.createObjectURL(r.data)))
      .catch(() => toast.error("Erreur génération QR"));
  }, [emp.id]);

  const print = () => {
    const w = window.open("", "_blank");
    w.document.write(`<html><body style="text-align:center;font-family:sans-serif;padding:20px">
      <img src="${src}" style="width:200px"><br>
      <strong style="font-size:18px">${emp.prenom} ${emp.nom}</strong><br>
      <span style="color:#666">${emp.poste || "Employé"} · ${emp.matricule}</span><br>
      <span style="font-size:12px;color:#999">HOTEL MONTANA</span>
    </body></html>`);
    w.document.close();
    w.print();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 320, textAlign: "center" }} onClick={e => e.stopPropagation()}>
        <h3>Badge QR — {emp.prenom} {emp.nom}</h3>
        <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 12 }}>{emp.matricule}</p>
        {src ? <img src={src} alt="QR" style={{ width: 200, height: 200, border: "1px solid var(--border)" }} />
             : <div style={{ width: 200, height: 200, background: "var(--bg)", margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "center" }}>Chargement…</div>}
        <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 16 }}>
          <button className="btn btn-primary btn-sm" onClick={print} disabled={!src}>Imprimer</button>
          <button className="btn btn-outline btn-sm" onClick={onClose}>Fermer</button>
        </div>
      </div>
    </div>
  );
}

const BLANK = { matricule:"", nom:"", prenom:"", poste:"", departement:"", telephone:"", email:"", date_embauche:"", statut:"Actif" };

export default function Employes() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [statut, setStatut] = useState("");
  const [form, setForm] = useState(BLANK);
  const [editId, setEditId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [qrEmp, setQrEmp] = useState(null);

  const load = () =>
    api.get(`/api/employes?q=${q}&statut=${statut}`).then(r => setRows(Array.isArray(r.data) ? r.data : [])).catch(() => {});

  useEffect(() => { load(); }, [q, statut]);

  const openAdd = () => { setForm(BLANK); setEditId(null); setShowForm(true); };
  const openEdit = (emp) => { setForm(emp); setEditId(emp.id); setShowForm(true); };

  const save = async (e) => {
    e.preventDefault();
    try {
      if (editId) { await api.put(`/api/employes/${editId}`, form); toast.success("Modifié"); }
      else        { await api.post("/api/employes", form); toast.success("Employé ajouté"); }
      setShowForm(false); load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erreur"); }
  };

  const del = async (id) => {
    if (!confirm("Supprimer ?")) return;
    await api.delete(`/api/employes/${id}`); load();
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">💼 Employés</h1>
        <button className="btn btn-success btn-sm" onClick={openAdd}>+ Ajouter</button>
      </div>

      <div className="toolbar">
        <input className="form-control" style={{ maxWidth:260 }} placeholder="Rechercher…"
          value={q} onChange={e => setQ(e.target.value)} />
        <select className="form-select" style={{ width:130 }} value={statut} onChange={e => setStatut(e.target.value)}>
          <option value="">Tous</option><option>Actif</option><option>Inactif</option>
        </select>
        <span style={{ color:"var(--muted)", fontSize:12 }}>{rows.length} employé(s)</span>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>{editId ? "Modifier Employé" : "Ajouter Employé"}</h3>
            <form onSubmit={save}>
              <div className="form-row">
                {[["Matricule *","matricule"],["Nom *","nom"],["Prénom *","prenom"],
                  ["Poste","poste"],["Département","departement"],["Téléphone","telephone"],
                  ["Email","email"],["Date Embauche","date_embauche"]].map(([lbl,key]) => (
                  <div key={key} className="form-group">
                    <label>{lbl}</label>
                    <input className="form-control" value={form[key] || ""}
                      required={lbl.includes("*")}
                      onChange={e => setForm({...form, [key]: e.target.value})} />
                  </div>
                ))}
                <div className="form-group">
                  <label>Statut</label>
                  <select className="form-select" value={form.statut}
                    onChange={e => setForm({...form, statut: e.target.value})}>
                    <option>Actif</option><option>Inactif</option>
                  </select>
                </div>
              </div>
              <div style={{ display:"flex", gap:8, justifyContent:"flex-end", marginTop:12 }}>
                <button type="button" className="btn btn-outline" onClick={() => setShowForm(false)}>Annuler</button>
                <button type="submit" className="btn btn-primary">Enregistrer</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {qrEmp && <QRModal emp={qrEmp} onClose={() => setQrEmp(null)} />}

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead><tr><th>Matricule</th><th>Nom</th><th>Poste</th><th>Département</th><th>Téléphone</th><th>Statut</th><th></th></tr></thead>
            <tbody>
              {rows.map(e => (
                <tr key={e.id} style={{ opacity: e.statut==="Inactif"?0.5:1 }}>
                  <td><code style={{fontSize:12}}>{e.matricule}</code></td>
                  <td>{e.prenom} <strong>{e.nom}</strong></td>
                  <td style={{ color:"var(--muted)" }}>{e.poste||"—"}</td>
                  <td style={{ color:"var(--muted)" }}>{e.departement||"—"}</td>
                  <td style={{ color:"var(--muted)", fontSize:12 }}>{e.telephone||"—"}</td>
                  <td><span className={`badge ${e.statut==="Actif"?"badge-success":"badge-muted"}`}>{e.statut}</span></td>
                  <td style={{ display:"flex", gap:4 }}>
                    <button className="btn btn-icon btn-sm" title="Badge QR" onClick={() => setQrEmp(e)}>QR</button>
                    <button className="btn btn-icon btn-sm" onClick={() => openEdit(e)}>✏️</button>
                    <button className="btn btn-icon btn-sm" onClick={() => del(e.id)}>🗑</button>
                  </td>
                </tr>
              ))}
              {rows.length===0 && <tr><td colSpan={7} className="empty">Aucun employé</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
