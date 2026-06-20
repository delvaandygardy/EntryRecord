import { useEffect, useRef, useState } from "react";
import api from "../api";
import toast from "react-hot-toast";
import Hls from "hls.js";

function LiveFeed({ cam, onClose }) {
  const videoRef = useRef(null);
  const hlsRef = useRef(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const hlsUrl = `/hls/camera${cam.id}/index.m3u8`;
    const video = videoRef.current;
    if (!video) return;

    if (Hls.isSupported()) {
      const hls = new Hls({
        lowLatencyMode: true,
        backBufferLength: 0,
        liveSyncDurationCount: 2,
        liveMaxLatencyDurationCount: 4,
        maxLiveSyncPlaybackRate: 1.5,
        liveSyncOnStallIncrease: 0.5,
      });
      hlsRef.current = hls;
      hls.loadSource(hlsUrl);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        setLoading(false);
        video.play().catch(() => {});
      });
      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) setError("Impossible d'ouvrir le flux caméra");
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = hlsUrl;
      video.addEventListener("loadedmetadata", () => setLoading(false));
    } else {
      setError("Navigateur non compatible HLS");
    }
    return () => hlsRef.current?.destroy();
  }, [cam.id]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 980, width: "95%" }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>📷 {cam.nom} — Flux live</h3>
          <button className="btn btn-outline btn-sm" onClick={onClose}>✕ Fermer</button>
        </div>
        {error
          ? <div className="alert alert-danger">{error}</div>
          : <>
              {loading && <div style={{ textAlign: "center", padding: 40, color: "var(--muted)" }}>Connexion au flux...</div>}
              <video ref={videoRef} muted autoPlay controls
                style={{ width: "100%", borderRadius: 8, background: "#000", display: loading ? "none" : "block" }} />
            </>
        }
        <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 8 }}>
          Flux HLS via MediaMTX — latence ~1-2s
        </div>
      </div>
    </div>
  );
}

export default function Cameras() {
  const [cams, setCams] = useState([]);
  const [form, setForm] = useState({ nom: "", url_rtsp: "", point_entree: "Principal", actif: true });
  const [showForm, setShowForm] = useState(false);
  const [liveCam, setLiveCam] = useState(null);

  const load = () => api.get("/api/cameras").then(r => setCams(Array.isArray(r.data) ? r.data : [])).catch(() => {});
  useEffect(() => { load(); }, []);

  const save = async (e) => {
    e.preventDefault();
    try {
      await api.post("/api/cameras", form);
      toast.success("Caméra ajoutée");
      setShowForm(false);
      setForm({ nom: "", url_rtsp: "", point_entree: "Principal", actif: true });
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erreur"); }
  };

  const toggleAnpr = async (cam) => {
    const action = cam.streaming ? "stop" : "start";
    try {
      await api.post(`/api/cameras/${cam.id}/${action}`);
      toast.success(cam.streaming ? "Stream ANPR arrêté" : "Stream ANPR démarré");
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Erreur"); }
  };

  const del = async (id) => {
    if (!confirm("Supprimer cette caméra ?")) return;
    await api.delete(`/api/cameras/${id}`);
    load();
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">📷 Caméras IP</h1>
        <button className="btn btn-success btn-sm" onClick={() => setShowForm(true)}>+ Ajouter Caméra</button>
      </div>

      <div className="alert alert-warning" style={{ marginBottom: 16 }}>
        ℹ️ Protocole RTSP. Exemple : <code>rtsp://admin:pass@192.168.1.100:554/stream</code>
      </div>

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>📷 Ajouter une caméra IP</h3>
            <form onSubmit={save}>
              <div className="form-group"><label>Nom *</label>
                <input className="form-control" required value={form.nom}
                  onChange={e => setForm({...form, nom: e.target.value})}
                  placeholder="Caméra Entrée Principale" /></div>
              <div className="form-group"><label>URL RTSP *</label>
                <input className="form-control" required value={form.url_rtsp}
                  onChange={e => setForm({...form, url_rtsp: e.target.value})}
                  placeholder="rtsp://admin:pass@192.168.1.x:554/stream" /></div>
              <div className="form-group"><label>Point d'entrée</label>
                <select className="form-select" value={form.point_entree}
                  onChange={e => setForm({...form, point_entree: e.target.value})}>
                  <option>Principal</option>
                  <option>Entrée Nord</option>
                  <option>Entrée Sud</option>
                </select></div>
              <div style={{ display:"flex", gap:8, justifyContent:"flex-end" }}>
                <button type="button" className="btn btn-outline" onClick={() => setShowForm(false)}>Annuler</button>
                <button type="submit" className="btn btn-primary">Ajouter</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {liveCam && <LiveFeed cam={liveCam} onClose={() => setLiveCam(null)} />}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(300px,1fr))", gap: 16 }}>
        {cams.map(cam => (
          <div key={cam.id} className="card">
            <div className="card-header" style={{ justifyContent: "space-between" }}>
              <span>{cam.nom}</span>
              <span className={`badge ${cam.streaming ? "badge-success" : "badge-muted"}`}>
                {cam.streaming ? "🟢 ANPR ACTIF" : "⚫ INACTIF"}
              </span>
            </div>
            <div style={{ padding: 16 }}>
              <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 8, wordBreak:"break-all" }}>
                {cam.url_rtsp}
              </div>
              <div style={{ fontSize: 12, marginBottom: 12 }}>📍 {cam.point_entree}</div>
              <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
                <button
                  className={`btn btn-sm ${cam.streaming ? "btn-danger" : "btn-success"}`}
                  onClick={() => toggleAnpr(cam)}>
                  {cam.streaming ? "⏹ Arrêter ANPR" : "▶ Démarrer ANPR"}
                </button>
                <button className="btn btn-outline btn-sm" onClick={() => setLiveCam(cam)}>
                  🎥 Voir Live
                </button>
                <button className="btn btn-icon btn-sm" onClick={() => del(cam.id)}>🗑</button>
              </div>
            </div>
          </div>
        ))}
        {cams.length === 0 && (
          <div className="card"><div className="empty">Aucune caméra configurée</div></div>
        )}
      </div>
    </div>
  );
}
