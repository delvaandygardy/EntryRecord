import { useEffect, useRef, useState } from "react";
import api from "../api";
import toast from "react-hot-toast";

function ManualPlateEntry({ result, saving, onSave }) {
  const [plate, setPlate] = useState("");
  return (
    <div>
      {result.anpr_error && (
        <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 8, padding: "6px 10px", background: "var(--surface2)", borderRadius: 6 }}>
          ℹ️ Reconnaissance automatique indisponible. Entrez la plaque manuellement.
        </div>
      )}
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input
          className="form-control"
          placeholder="Plaque d'immatriculation…"
          value={plate}
          onChange={e => setPlate(e.target.value.toUpperCase())}
          style={{ fontFamily: "monospace", fontSize: 16, letterSpacing: 2, flex: 1 }}
          autoFocus
        />
        <button
          className="btn btn-success"
          disabled={!plate.trim() || saving === plate}
          onClick={() => onSave(plate.trim(), 1.0, result.point_entree)}
        >
          {saving === plate ? "…" : "Enregistrer"}
        </button>
      </div>
    </div>
  );
}

function CaptureModal({ cameras, onClose, onSaved }) {
  const [camId, setCamId] = useState(cameras[0]?.id || "");
  const [loading, setLoading] = useState(false);
  const [anprLoading, setAnprLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [plates, setPlates] = useState([]);
  const [saving, setSaving] = useState(null);

  const capture = async () => {
    if (!camId) return;
    setLoading(true);
    setResult(null);
    setPlates([]);
    try {
      // Étape 1 : capture image (rapide ~10s)
      const { data } = await api.post(`/api/cameras/${camId}/capture`);
      setResult(data);
      setLoading(false);
      // Étape 2 : ANPR en arrière-plan (lent, mais l'image est déjà affichée)
      setAnprLoading(true);
      try {
        const { data: anprData } = await api.post(`/api/cameras/${camId}/anpr`, {
          image_path: data.image_path,
        });
        setPlates(anprData.plates || []);
      } catch {
        setPlates([]);
      } finally {
        setAnprLoading(false);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Erreur de capture");
      setLoading(false);
    }
  };

  const savePlate = async (plate, confidence, point_entree) => {
    setSaving(plate);
    try {
      const { data } = await api.post("/api/vehicules", {
        plaque: plate,
        confidence,
        point_entree,
        notes: `Capturé via ${result?.camera_nom || "caméra"}`,
      });
      if (data.blacklist) toast.error(`⚠️ Plaque ${plate} en liste noire !`);
      else toast.success(`Plaque ${plate} enregistrée`);
      onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Erreur");
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 700, width: "95%" }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3 style={{ margin: 0 }}>📷 Capture ANPR</h3>
          <button className="btn btn-outline btn-sm" onClick={onClose}>✕</button>
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <select className="form-select" value={camId} onChange={e => setCamId(e.target.value)} style={{ flex: 1 }}>
            {cameras.map(c => <option key={c.id} value={c.id}>{c.nom} — {c.point_entree}</option>)}
          </select>
          <button className="btn btn-primary" onClick={capture} disabled={loading || !camId}>
            {loading ? "Capture…" : "📸 Capturer"}
          </button>
        </div>

        {loading && (
          <div style={{ textAlign: "center", padding: 40, color: "var(--muted)" }}>
            Connexion à la caméra et analyse ANPR…
          </div>
        )}

        {result && (
          <div>
            <img
              src={result.image_path}
              alt="Capture"
              style={{ width: "100%", borderRadius: 8, marginBottom: 12, maxHeight: 360, objectFit: "contain", background: "#000" }}
            />

            {anprLoading && (
              <div style={{ padding: "10px 14px", background: "var(--surface2)", borderRadius: 8, marginBottom: 10,
                display: "flex", alignItems: "center", gap: 10, fontSize: 13, color: "var(--muted)" }}>
                <span style={{ animation: "pulse 1s infinite", display:"inline-block" }}>⏳</span>
                Analyse ANPR en cours… (peut prendre 30-60s)
              </div>
            )}

            {!anprLoading && plates.length > 0 ? (
              <div>
                <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 13 }}>Plaques détectées :</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {plates.map((p, i) => (
                    <div key={i} style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "10px 14px", background: "var(--surface2)", borderRadius: 8,
                      border: "1px solid var(--border)"
                    }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        <span style={{
                          fontFamily: "monospace", fontSize: 20, fontWeight: 700,
                          letterSpacing: 3, color: "#f0f6fc"
                        }}>{p.plate}</span>
                        <span style={{
                          background: p.confidence > 0.8 ? "#238636" : p.confidence > 0.5 ? "#9e6a03" : "#b62324",
                          color: "#fff", borderRadius: 4, padding: "2px 8px", fontSize: 11
                        }}>
                          {(p.confidence * 100).toFixed(0)}%
                        </span>
                        <span style={{ color: "var(--muted)", fontSize: 11 }}>{p.source}</span>
                      </div>
                      <button
                        className="btn btn-success btn-sm"
                        disabled={saving === p.plate}
                        onClick={() => savePlate(p.plate, p.confidence, result.point_entree)}
                      >
                        {saving === p.plate ? "…" : "Enregistrer"}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            ) : !anprLoading && (
              <ManualPlateEntry
                result={result}
                saving={saving}
                onSave={savePlate}
              />
            )}

            <div style={{ marginTop: 12 }}>
              <button className="btn btn-outline btn-sm" onClick={capture} disabled={loading}>
                📸 Nouvelle capture
              </button>
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
  const [form, setForm] = useState({ plaque: "", point_entree: "Principal", notes: "" });
  const [showForm, setShowForm] = useState(false);
  const [showCapture, setShowCapture] = useState(false);
  const [cameras, setCameras] = useState([]);
  const [points] = useState(["Principal", "Entrée Nord", "Entrée Sud"]);

  const load = () => api.get(`/api/vehicules?q=${q}&limit=300`).then(r => setRows(Array.isArray(r.data) ? r.data : [])).catch(() => {});

  useEffect(() => { load(); }, [q]);
  useEffect(() => {
    api.get("/api/cameras").then(r => setCameras(Array.isArray(r.data) ? r.data : [])).catch(() => {});
  }, []);

  const save = async (e) => {
    e.preventDefault();
    try {
      const { data } = await api.post("/api/vehicules", form);
      if (data.blacklist) toast.error(`⚠️ Plaque ${form.plaque} en liste noire !`);
      else toast.success("Véhicule enregistré");
      setForm({ plaque: "", point_entree: "Principal", notes: "" });
      setShowForm(false);
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erreur"); }
  };

  const del = async (id) => {
    if (!confirm("Supprimer ?")) return;
    await api.delete(`/api/vehicules/${id}`);
    load();
  };

  const exportCsv = () => window.open("/export/vehicules");

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">🚗 Véhicules</h1>
        <div style={{ display: "flex", gap: 8 }}>
          {cameras.length > 0 && (
            <button className="btn btn-primary btn-sm" onClick={() => setShowCapture(true)}>
              📸 Capturer ANPR
            </button>
          )}
          <button className="btn btn-success btn-sm" onClick={() => setShowForm(true)}>+ Ajouter</button>
          <button className="btn btn-outline btn-sm" onClick={exportCsv}>⬇ CSV</button>
        </div>
      </div>

      <div className="toolbar">
        <input className="form-control" style={{ maxWidth: 300 }} placeholder="Rechercher plaque…"
          value={q} onChange={e => setQ(e.target.value)} />
        <span style={{ color: "var(--muted)", fontSize: 12 }}>{rows.length} résultat(s)</span>
      </div>

      {showCapture && cameras.length > 0 && (
        <CaptureModal
          cameras={cameras}
          onClose={() => setShowCapture(false)}
          onSaved={() => { load(); }}
        />
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
                <th>ID</th><th>Plaque</th><th>Confiance</th><th>Entrée</th><th>Date/Heure</th><th>Notes</th><th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map(v => (
                <tr key={v.id}>
                  <td style={{ color: "var(--muted)" }}>{v.id}</td>
                  <td><span className="badge badge-primary">{v.plaque}</span></td>
                  <td>
                    {v.confidence ? (
                      <span style={{
                        color: v.confidence > 0.8 ? "#3fb950" : v.confidence > 0.5 ? "#e3b341" : "#f85149"
                      }}>
                        {(v.confidence * 100).toFixed(0)}%
                      </span>
                    ) : "—"}
                  </td>
                  <td>{v.point_entree}</td>
                  <td style={{ color: "var(--muted)", fontSize: 12 }}>{v.timestamp?.slice(0, 16)}</td>
                  <td style={{ color: "var(--muted)", fontSize: 12 }}>{v.notes || "—"}</td>
                  <td><button className="btn btn-icon btn-sm" onClick={() => del(v.id)}>🗑</button></td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={7} className="empty">Aucun véhicule</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
