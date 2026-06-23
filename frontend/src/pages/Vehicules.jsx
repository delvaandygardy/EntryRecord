import { useEffect, useState } from "react";
import api from "../api";
import toast from "react-hot-toast";

const COLOR_MAP = {
  rouge: "#c0392b", bleu: "#2980b9", blanc: "#ecf0f1", noir: "#1a1a1a",
  gris: "#7f8c8d", argent: "#bdc3c7", vert: "#27ae60", jaune: "#f1c40f",
  orange: "#e67e22", marron: "#795548", beige: "#d4b896", violet: "#8e44ad",
};

function ConducteurSelect({ value, onChange, conducteurs }) {
  return (
    <select className="form-select" value={value} onChange={e => onChange(e.target.value)}>
      <option value="">— Aucun conducteur —</option>
      {conducteurs.map(c => (
        <option key={c.id} value={c.id}>{c.nom} {c.prenom}</option>
      ))}
    </select>
  );
}

function ManualPlateEntry({ result, saving, onSave, conducteurs }) {
  const [plate, setPlate] = useState("");
  const [condId, setCondId] = useState("");
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {result.anpr_error && (
        <div style={{ fontSize: 12, color: "var(--muted)", padding: "6px 10px", background: "var(--surface2)", borderRadius: 6 }}>
          ℹ️ Reconnaissance automatique indisponible. Entrez la plaque manuellement.
        </div>
      )}
      <input
        className="form-control"
        placeholder="Plaque d'immatriculation…"
        value={plate}
        onChange={e => setPlate(e.target.value.toUpperCase())}
        style={{ fontFamily: "monospace", fontSize: 16, letterSpacing: 2 }}
        autoFocus
      />
      <ConducteurSelect value={condId} onChange={setCondId} conducteurs={conducteurs} />
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button
          className="btn btn-success"
          disabled={!plate.trim() || saving === plate}
          onClick={() => onSave(plate.trim(), 1.0, result.point_entree, condId ? parseInt(condId) : null)}
        >
          {saving === plate ? "…" : "Enregistrer"}
        </button>
      </div>
    </div>
  );
}

function CaptureModal({ cameras, conducteurs, onClose, onSaved }) {
  const [camId, setCamId] = useState(cameras[0]?.id || "");
  const [loading, setLoading] = useState(false);
  const [anprLoading, setAnprLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [plates, setPlates] = useState([]);
  const [saving, setSaving] = useState(null);
  const [condId, setCondId] = useState("");

  const capture = async () => {
    if (!camId) return;
    setLoading(true);
    setResult(null);
    setPlates([]);
    try {
      const { data } = await api.post(`/api/cameras/${camId}/capture`);
      setResult(data);
      setLoading(false);
      setAnprLoading(true);
      try {
        const { data: anprData } = await api.post(`/api/cameras/${camId}/anpr`, { image_path: data.image_path });
        setPlates(anprData.plates || []);
      } catch { setPlates([]); }
      finally { setAnprLoading(false); }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Erreur de capture");
      setLoading(false);
    }
  };

  const savePlate = async (plate, confidence, point_entree, cid) => {
    setSaving(plate);
    try {
      const { data } = await api.post("/api/vehicules", {
        plaque: plate, confidence, point_entree,
        notes: `Capturé via ${result?.camera_nom || "caméra"}`,
        conducteur_id: cid ?? (condId ? parseInt(condId) : null),
      });
      if (data.blacklist) toast.error(`⚠️ Plaque ${plate} en liste noire !`);
      else if (data.action === "SORTIE") toast.success(`🚗 SORTIE enregistrée — ${plate}`, { duration: 5000 });
      else toast.success(`🟢 ENTRÉE enregistrée — ${plate}`, { duration: 5000 });
      onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Erreur");
    } finally { setSaving(null); }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 700, width: "95%" }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>📷 Capture ANPR</h3>
          <button className="btn btn-outline btn-sm" onClick={onClose}>✕</button>
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <select className="form-select" value={camId} onChange={e => setCamId(e.target.value)} style={{ flex: 1 }}>
            {cameras.map(c => <option key={c.id} value={c.id}>{c.nom} — {c.point_entree}</option>)}
          </select>
          <button className="btn btn-primary" onClick={capture} disabled={loading || !camId}>
            {loading ? "Capture…" : "📸 Capturer"}
          </button>
        </div>

        <div className="form-group" style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 12, color: "var(--muted)", display: "block", marginBottom: 4 }}>Conducteur associé</label>
          <ConducteurSelect value={condId} onChange={setCondId} conducteurs={conducteurs} />
        </div>

        {loading && (
          <div style={{ textAlign: "center", padding: 40, color: "var(--muted)" }}>
            Connexion à la caméra et analyse ANPR…
          </div>
        )}

        {result && (
          <div>
            <img src={result.image_path} alt="Capture"
              style={{ width: "100%", borderRadius: 8, marginBottom: 12, maxHeight: 360, objectFit: "contain", background: "#000" }} />

            {anprLoading && (
              <div style={{ padding: "10px 14px", background: "var(--surface2)", borderRadius: 8, marginBottom: 10,
                display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: "var(--muted)" }}>
                <span>⏳</span> Analyse ANPR en cours… (peut prendre 30-60s)
              </div>
            )}

            {!anprLoading && plates.length > 0 ? (
              <div>
                <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 13 }}>Plaques détectées :</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {plates.map((p, i) => (
                    <div key={i} style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "10px 14px", background: "var(--surface2)", borderRadius: 8, border: "1px solid var(--border)"
                    }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <span style={{ fontFamily: "monospace", fontSize: 20, fontWeight: 700, letterSpacing: 3, color: "#f0f6fc" }}>{p.plate}</span>
                        <span style={{
                          background: p.confidence > 0.8 ? "#238636" : p.confidence > 0.5 ? "#9e6a03" : "#b62324",
                          color: "#fff", borderRadius: 4, padding: "2px 8px", fontSize: 11
                        }}>{(p.confidence * 100).toFixed(0)}%</span>
                        <span style={{ color: "var(--muted)", fontSize: 11 }}>{p.source}</span>
                      </div>
                      <button className="btn btn-success btn-sm" disabled={saving === p.plate}
                        onClick={() => savePlate(p.plate, p.confidence, result.point_entree, null)}>
                        {saving === p.plate ? "…" : "Enregistrer"}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ) : !anprLoading && (
              <ManualPlateEntry result={result} saving={saving} onSave={savePlate} conducteurs={conducteurs} />
            )}

            <div style={{ marginTop: 12 }}>
              <button className="btn btn-outline btn-sm" onClick={capture} disabled={loading}>📸 Nouvelle capture</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Vehicules() {
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");
  const [form, setForm] = useState({ plaque: "", point_entree: "Principal", notes: "", conducteur_id: "" });
  const [showForm, setShowForm] = useState(false);
  const [showCapture, setShowCapture] = useState(false);
  const [cameras, setCameras] = useState([]);
  const [conducteurs, setConducteurs] = useState([]);
  const [points] = useState(["Principal", "Entrée Nord", "Entrée Sud"]);

  const load = () =>
    api.get(`/api/vehicules?q=${q}&limit=300`)
      .then(r => setRows(Array.isArray(r.data) ? r.data : []))
      .catch(() => {});

  const loadConducteurs = () =>
    api.get("/api/conducteurs?limit=200")
      .then(r => {
        const all = Array.isArray(r.data) ? r.data : [];
        setConducteurs(all.filter(c => !c.heure_sortie));
      })
      .catch(() => {});

  useEffect(() => { load(); }, [q]);
  useEffect(() => {
    api.get("/api/cameras").then(r => setCameras(Array.isArray(r.data) ? r.data : [])).catch(() => {});
    loadConducteurs();
  }, []);

  const save = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...form,
        conducteur_id: form.conducteur_id ? parseInt(form.conducteur_id) : null,
      };
      const { data } = await api.post("/api/vehicules", payload);
      if (data.blacklist) toast.error(`⚠️ Plaque ${form.plaque} en liste noire !`);
      else if (data.action === "SORTIE") toast.success(`🚗 SORTIE enregistrée — ${form.plaque}`, { duration: 5000 });
      else toast.success(`🟢 ENTRÉE enregistrée — ${form.plaque}`, { duration: 5000 });
      setForm({ plaque: "", point_entree: "Principal", notes: "", conducteur_id: "" });
      setShowForm(false);
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erreur"); }
  };

  const sortie = async (id) => {
    try {
      await api.patch(`/api/vehicules/${id}/sortie`, { point_sortie: "Principal" });
      toast.success("Sortie enregistrée");
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erreur"); }
  };

  const del = async (id) => {
    if (!confirm("Supprimer ?")) return;
    await api.delete(`/api/vehicules/${id}`);
    load();
  };

  const exportCsv = () => window.open("/export/vehicules");

  const enCours = rows.filter(v => !v.heure_sortie).length;

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">🚗 Véhicules
          {enCours > 0 && (
            <span style={{ marginLeft: 10, fontSize: 13, fontWeight: 400, color: "#3fb950",
              background: "rgba(63,185,80,0.12)", borderRadius: 12, padding: "2px 10px" }}>
              {enCours} en cours
            </span>
          )}
        </h1>
        <div style={{ display: "flex", gap: 8 }}>
          {cameras.length > 0 && (
            <button className="btn btn-primary btn-sm" onClick={() => { loadConducteurs(); setShowCapture(true); }}>
              📸 Capturer ANPR
            </button>
          )}
          <button className="btn btn-success btn-sm" onClick={() => { loadConducteurs(); setShowForm(true); }}>+ Ajouter</button>
          <button className="btn btn-outline btn-sm" onClick={exportCsv}>⬇ CSV</button>
        </div>
      </div>

      <div className="toolbar">
        <input className="form-control" style={{ maxWidth: 300 }} placeholder="Rechercher plaque…"
          value={q} onChange={e => setQ(e.target.value)} />
        <span style={{ color: "var(--muted)", fontSize: 12 }}>{rows.length} résultat(s)</span>
      </div>

      {showCapture && cameras.length > 0 && (
        <CaptureModal cameras={cameras} conducteurs={conducteurs}
          onClose={() => setShowCapture(false)}
          onSaved={() => { load(); }} />
      )}

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Ajouter un véhicule</h3>
            <form onSubmit={save}>
              <div className="form-group">
                <label>Plaque *</label>
                <input className="form-control" required autoFocus
                  value={form.plaque} onChange={e => setForm({ ...form, plaque: e.target.value.toUpperCase() })} />
              </div>
              <div className="form-group">
                <label>Point d'entrée</label>
                <select className="form-select" value={form.point_entree}
                  onChange={e => setForm({ ...form, point_entree: e.target.value })}>
                  {points.map(p => <option key={p}>{p}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Conducteur</label>
                <ConducteurSelect value={form.conducteur_id} onChange={v => setForm({ ...form, conducteur_id: v })} conducteurs={conducteurs} />
              </div>
              <div className="form-group">
                <label>Notes</label>
                <input className="form-control" value={form.notes}
                  onChange={e => setForm({ ...form, notes: e.target.value })} />
              </div>
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
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
            <thead>
              <tr>
                <th>Statut</th>
                <th>Plaque</th>
                <th>Type</th>
                <th>Couleur</th>
                <th>Conducteur</th>
                <th>Confiance</th>
                <th>Point Entrée</th>
                <th>Heure Entrée</th>
                <th>Point Sortie</th>
                <th>Heure Sortie</th>
                <th>Notes</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map(v => (
                <tr key={v.id}>
                  <td>
                    {v.heure_sortie
                      ? <span className="badge" style={{ background: "var(--surface2)", color: "var(--muted)" }}>Sorti</span>
                      : <span className="badge badge-success">En cours</span>}
                  </td>
                  <td><span className="badge badge-primary">{v.plaque}</span></td>
                  <td style={{ fontSize: 12, color: "var(--muted)" }}>
                    {v.type_vehicule || <span style={{ color: "var(--muted)" }}>—</span>}
                    {v.region_plaque && <span style={{ fontSize: 10, marginLeft: 4, opacity: 0.6 }}>[{v.region_plaque.toUpperCase()}]</span>}
                  </td>
                  <td style={{ fontSize: 12 }}>
                    {v.couleur_vehicule
                      ? <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
                          <span style={{
                            width: 12, height: 12, borderRadius: "50%", display: "inline-block",
                            background: COLOR_MAP[v.couleur_vehicule] || "#888",
                            border: "1px solid rgba(255,255,255,0.2)",
                          }} />
                          {v.couleur_vehicule}
                        </span>
                      : <span style={{ color: "var(--muted)" }}>—</span>}
                  </td>
                  <td style={{ fontSize: 13 }}>
                    {v.conducteur_nom
                      ? `${v.conducteur_nom}${v.conducteur_prenom ? " " + v.conducteur_prenom : ""}`
                      : <span style={{ color: "var(--muted)" }}>—</span>}
                  </td>
                  <td>
                    {v.confidence != null
                      ? <span style={{ color: v.confidence > 0.8 ? "#3fb950" : v.confidence > 0.5 ? "#e3b341" : "#f85149" }}>
                          {(v.confidence * 100).toFixed(0)}%
                        </span>
                      : "—"}
                  </td>
                  <td style={{ fontSize: 12 }}>{v.point_entree || "—"}</td>
                  <td style={{ color: "var(--muted)", fontSize: 12 }}>{v.timestamp?.slice(0, 16) || "—"}</td>
                  <td style={{ fontSize: 12 }}>{v.point_sortie || "—"}</td>
                  <td style={{ color: "var(--muted)", fontSize: 12 }}>{v.heure_sortie?.slice(0, 16) || "—"}</td>
                  <td style={{ color: "var(--muted)", fontSize: 12 }}>{v.notes || "—"}</td>
                  <td style={{ display: "flex", gap: 4, flexWrap: "nowrap" }}>
                    {!v.heure_sortie && (
                      <button className="btn btn-sm" style={{ background: "#b62324", color: "#fff" }}
                        onClick={() => sortie(v.id)}>
                        Sortie
                      </button>
                    )}
                    <button className="btn btn-icon btn-sm" onClick={() => del(v.id)}>🗑</button>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={12} className="empty">Aucun véhicule</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
