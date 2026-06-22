import { useEffect, useState } from "react";
import api from "../api";
import toast from "react-hot-toast";
import DocumentScanner from "../components/DocumentScanner";

function QRModal({ person, type, onClose }) {
  const [src, setSrc] = useState(null);
  const endpoint = type === "conducteur" ? "conducteur" : "pieton";
  useEffect(() => {
    api.get(`/api/qr/${endpoint}/${person.id}`, { responseType: "blob" })
      .then(r => setSrc(URL.createObjectURL(r.data)))
      .catch(() => toast.error("Erreur génération QR"));
  }, [person.id]);

  const print = () => {
    const w = window.open("", "_blank");
    w.document.write(`<html><body style="text-align:center;font-family:sans-serif;padding:20px">
      <img src="${src}" style="width:200px"><br>
      <strong style="font-size:18px">${person.prenom || ""} ${person.nom || ""}</strong><br>
      <span style="color:#666">${type === "conducteur" ? "Conducteur" : "Piéton"} · ${person.numero_document || "—"}</span><br>
      <span style="font-size:12px;color:#999">HOTEL MONTANA</span>
    </body></html>`);
    w.document.close();
    w.print();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 320, textAlign: "center" }} onClick={e => e.stopPropagation()}>
        <h3>Badge QR — {person.prenom} {person.nom}</h3>
        <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 12 }}>{person.numero_document || "—"}</p>
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

const BLANK = { nom:"", prenom:"", numero_document:"", type_document:"CNI", date_naissance:"", nationalite:"HTI", date_expiration:"", point_entree:"Principal" };

export default function Personnes({ mode }) {
  const isConducteur = mode === "conducteur";
  const title = isConducteur ? "🪪 Conducteurs" : "🚶 Piétons";
  const endpoint = isConducteur ? "/api/conducteurs" : "/api/pietons";

  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [form, setForm] = useState(BLANK);
  const [showForm, setShowForm] = useState(false);
  const [qrPerson, setQrPerson] = useState(null);
  const [showScanner, setShowScanner] = useState(false);

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

  const sortie = async (id) => {
    try {
      await api.patch(`${endpoint}/${id}/sortie`, { point_sortie: "Principal" });
      toast.success("Sortie enregistrée");
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erreur sortie"); }
  };

  const docTypes = isConducteur
    ? ["PERMIS","CNI","PASSEPORT"]
    : ["CNI","PASSEPORT","TITRE_SEJOUR","AUTRE"];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">{title}</h1>
        <button className="btn btn-outline btn-sm" onClick={() => setShowScanner(true)}>🔍 Scanner</button>
        <button className="btn btn-success btn-sm" onClick={() => setShowForm(true)}>+ Ajouter</button>
      </div>

      <div className="toolbar">
        <input className="form-control" style={{ maxWidth:300 }} placeholder="Rechercher nom, document…"
          value={q} onChange={e => setQ(e.target.value)} />
        <span style={{ color:"var(--muted)", fontSize:12 }}>{rows.length} résultat(s)</span>
      </div>

      {showScanner && (
        <DocumentScanner
          onResult={(fields) => {
            setForm(prev => ({ ...prev, ...fields }));
            setShowScanner(false);
            setShowForm(true);
            toast.success("Formulaire rempli automatiquement");
          }}
          onClose={() => setShowScanner(false)}
        />
      )}

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ margin: 0 }}>Enregistrer {isConducteur ? "un conducteur" : "un piéton"}</h3>
              <button type="button" className="btn btn-outline btn-sm"
                onClick={() => { setShowForm(false); setShowScanner(true); }}>
                🔍 Scanner document
              </button>
            </div>
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

      {qrPerson && <QRModal person={qrPerson} type={mode} onClose={() => setQrPerson(null)} />}

      <div className="card">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Nom</th>
                <th>N° Document</th>
                <th>Statut</th>
                <th>Point Entrée</th>
                <th>Heure Entrée</th>
                <th>Point Sortie</th>
                <th>Heure Sortie</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map(r => {
                const inside = !r.heure_sortie;
                return (
                  <tr key={r.id}>
                    <td>{r.prenom} <strong>{r.nom}</strong></td>
                    <td><code style={{fontSize:12}}>{r.numero_document||"—"}</code></td>
                    <td>
                      <span className={`badge ${inside ? "badge-success" : "badge-muted"}`}>
                        {inside ? "En cours" : "Sorti"}
                      </span>
                    </td>
                    <td style={{ color:"var(--muted)", fontSize:12 }}>{r.point_entree||"—"}</td>
                    <td style={{ color:"var(--muted)", fontSize:12 }}>{r.timestamp?.slice(0,16)||"—"}</td>
                    <td style={{ color:"var(--muted)", fontSize:12 }}>{r.point_sortie||"—"}</td>
                    <td style={{ fontSize:12 }}>
                      {r.heure_sortie
                        ? <span style={{ color:"var(--muted)" }}>{r.heure_sortie.slice(0,16)}</span>
                        : <button className="btn btn-sm" style={{ background:"#e53e3e", color:"#fff", padding:"2px 8px" }}
                            onClick={() => sortie(r.id)}>Sortie</button>
                      }
                    </td>
                    <td style={{ display:"flex", gap:4 }}>
                      <button className="btn btn-icon btn-sm" title="Badge QR" onClick={() => setQrPerson(r)}>QR</button>
                      <button className="btn btn-icon btn-sm" onClick={() => del(r.id)}>🗑</button>
                    </td>
                  </tr>
                );
              })}
              {rows.length===0 && <tr><td colSpan={8} className="empty">Aucun enregistrement</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
