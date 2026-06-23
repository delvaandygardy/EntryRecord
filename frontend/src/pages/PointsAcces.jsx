import { useEffect, useState } from "react";
import api from "../api";
import toast from "react-hot-toast";

export default function PointsAcces() {
  const [points, setPoints] = useState([]);
  const [nom, setNom] = useState("");
  const [editId, setEditId] = useState(null);
  const [editNom, setEditNom] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () =>
    api.get("/api/points_acces")
      .then(r => setPoints(Array.isArray(r.data) ? r.data : []))
      .catch(() => {});

  useEffect(() => { load(); }, []);

  const add = async (e) => {
    e.preventDefault();
    if (!nom.trim()) return;
    setSaving(true);
    try {
      await api.post("/api/points_acces", { nom: nom.trim() });
      toast.success(`Point "${nom.trim()}" ajouté`);
      setNom("");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Erreur");
    } finally { setSaving(false); }
  };

  const save = async (id) => {
    if (!editNom.trim()) return;
    try {
      await api.patch(`/api/points_acces/${id}`, { nom: editNom.trim() });
      toast.success("Renommé");
      setEditId(null);
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Erreur");
    }
  };

  const del = async (id, name) => {
    if (!confirm(`Supprimer "${name}" ?`)) return;
    try {
      await api.delete(`/api/points_acces/${id}`);
      toast.success("Supprimé");
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Erreur");
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">🚪 Points d'Accès</h1>
      </div>

      <div className="card" style={{ maxWidth: 560 }}>
        <form onSubmit={add} style={{ display: "flex", gap: 8, marginBottom: 20 }}>
          <input
            className="form-control"
            placeholder="Nom du nouveau point (ex: Parking Sud)"
            value={nom}
            onChange={e => setNom(e.target.value)}
            style={{ flex: 1 }}
            autoFocus
          />
          <button className="btn btn-success" type="submit" disabled={saving || !nom.trim()}>
            {saving ? "…" : "+ Ajouter"}
          </button>
        </form>

        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Nom</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {points.map(p => (
              <tr key={p.id}>
                <td style={{ color: "var(--muted)", width: 40 }}>{p.id}</td>
                <td>
                  {editId === p.id ? (
                    <input
                      className="form-control"
                      value={editNom}
                      onChange={e => setEditNom(e.target.value)}
                      onKeyDown={e => { if (e.key === "Enter") save(p.id); if (e.key === "Escape") setEditId(null); }}
                      autoFocus
                      style={{ maxWidth: 260 }}
                    />
                  ) : (
                    <span style={{ fontWeight: 500 }}>{p.nom}</span>
                  )}
                </td>
                <td style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                  {editId === p.id ? (
                    <>
                      <button className="btn btn-primary btn-sm" onClick={() => save(p.id)}>Sauver</button>
                      <button className="btn btn-outline btn-sm" onClick={() => setEditId(null)}>Annuler</button>
                    </>
                  ) : (
                    <>
                      <button className="btn btn-outline btn-sm"
                        onClick={() => { setEditId(p.id); setEditNom(p.nom); }}>
                        Renommer
                      </button>
                      {p.nom !== "Principal" && (
                        <button className="btn btn-icon btn-sm" onClick={() => del(p.id, p.nom)}>🗑</button>
                      )}
                    </>
                  )}
                </td>
              </tr>
            ))}
            {points.length === 0 && (
              <tr><td colSpan={3} className="empty">Aucun point d'accès</td></tr>
            )}
          </tbody>
        </table>

        <p style={{ marginTop: 16, fontSize: 12, color: "var(--muted)" }}>
          Le point "Principal" ne peut pas être supprimé. Les modifications sont immédiatement prises en compte dans tous les formulaires.
        </p>
      </div>
    </div>
  );
}
