import { useState } from "react";
import api from "../api";
import toast from "react-hot-toast";

const ALL_TABLES = ["vehicules","conducteurs","pietons","employes"];

export default function Reports() {
  const [fmt, setFmt] = useState("pdf");
  const [tables, setTables] = useState(ALL_TABLES);
  const [dateDebut, setDateDebut] = useState("");
  const [dateFin, setDateFin]   = useState("");
  const [loading, setLoading]   = useState(false);

  const toggle = (t) => setTables(prev => prev.includes(t) ? prev.filter(x=>x!==t) : [...prev, t]);

  const generate = async () => {
    if (!tables.length) { toast.error("Sélectionnez au moins un tableau"); return; }
    setLoading(true);
    try {
      const res = await api.post(`/api/reports/${fmt}`, {
        format: fmt, tables, date_debut: dateDebut || null, date_fin: dateFin || null
      }, { responseType: "blob" });
      const url  = URL.createObjectURL(res.data);
      const link = document.createElement("a");
      link.href  = url;
      link.download = `rapport_${new Date().toISOString().slice(0,10)}.${fmt === "pdf" ? "pdf" : "xlsx"}`;
      link.click();
      URL.revokeObjectURL(url);
      toast.success("Rapport généré !");
    } catch { toast.error("Erreur lors de la génération"); }
    finally { setLoading(false); }
  };

  const TABLE_LABELS = {
    vehicules:   "🚗 Véhicules",
    conducteurs: "🪪 Conducteurs",
    pietons:     "🚶 Piétons",
    employes:    "💼 Employés",
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">📊 Rapports</h1>
      </div>

      <div style={{ maxWidth: 580 }}>
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-header">Paramètres du rapport</div>
          <div style={{ padding: 20 }}>
            <div className="form-group">
              <label>Format</label>
              <div style={{ display:"flex", gap:8 }}>
                <button className={`btn ${fmt==="pdf"?"btn-primary":"btn-outline"}`} onClick={() => setFmt("pdf")}>
                  📄 PDF
                </button>
                <button className={`btn ${fmt==="excel"?"btn-success":"btn-outline"}`} onClick={() => setFmt("excel")}>
                  📊 Excel
                </button>
              </div>
            </div>

            <div className="form-group">
              <label>Tableaux inclus</label>
              <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
                {ALL_TABLES.map(t => (
                  <button key={t}
                    className={`btn btn-sm ${tables.includes(t)?"btn-primary":"btn-outline"}`}
                    onClick={() => toggle(t)}>
                    {TABLE_LABELS[t]}
                  </button>
                ))}
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Date début (optionnel)</label>
                <input type="date" className="form-control" value={dateDebut}
                  onChange={e => setDateDebut(e.target.value)} />
              </div>
              <div className="form-group">
                <label>Date fin (optionnel)</label>
                <input type="date" className="form-control" value={dateFin}
                  onChange={e => setDateFin(e.target.value)} />
              </div>
            </div>

            <button className="btn btn-primary" style={{ marginTop: 8, width:"100%" }}
              onClick={generate} disabled={loading}>
              {loading ? "Génération…" : `Générer ${fmt.toUpperCase()}`}
            </button>
          </div>
        </div>

        <div className="card">
          <div className="card-header">Exports rapides</div>
          <div style={{ padding: 16, display:"flex", gap:8, flexWrap:"wrap" }}>
            {ALL_TABLES.map(t => (
              <a key={t} href={`/export/${t}`}
                 className="btn btn-outline btn-sm" target="_blank">
                ⬇ {TABLE_LABELS[t]}
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
