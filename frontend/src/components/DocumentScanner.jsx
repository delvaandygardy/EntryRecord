import { useRef, useState, useEffect } from "react";
import api from "../api";
import toast from "react-hot-toast";

const MODES = [
  { id: "file",   label: "📁 Fichier / Scanner", desc: "Image scannée ou photo" },
  { id: "camera", label: "📷 Webcam",             desc: "Capturer depuis la caméra" },
  { id: "text",   label: "⌨️ Texte / MRZ",        desc: "Pistolet barcode ou lecteur MRZ" },
];

export default function DocumentScanner({ onResult, onClose }) {
  const [mode, setMode] = useState("file");
  const [loading, setLoading] = useState(false);
  const [camStream, setCamStream] = useState(null);
  const [mrzText, setMrzText] = useState("");
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileRef = useRef(null);
  const textRef = useRef(null);

  // Démarrer/arrêter la caméra selon le mode
  useEffect(() => {
    if (mode === "camera") {
      navigator.mediaDevices?.getUserMedia({ video: { facingMode: "environment" } })
        .then(stream => {
          setCamStream(stream);
          if (videoRef.current) videoRef.current.srcObject = stream;
        })
        .catch(() => toast.error("Caméra inaccessible"));
    } else {
      camStream?.getTracks().forEach(t => t.stop());
      setCamStream(null);
    }
    if (mode === "text") setTimeout(() => textRef.current?.focus(), 100);
    // eslint-disable-next-line
  }, [mode]);

  useEffect(() => () => camStream?.getTracks().forEach(t => t.stop()), [camStream]);

  const sendImage = async (blob) => {
    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", blob, "doc.jpg");
      const { data } = await api.post("/api/scan/document", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Document lu avec succès");
      onResult(data);
      onClose();
    } catch (err) {
      const msg = err.response?.data?.detail || "Document non reconnu";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (f) sendImage(f);
    e.target.value = "";
  };

  const captureCamera = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    canvas.toBlob(blob => sendImage(blob), "image/jpeg", 0.92);
  };

  const handleMrzText = async () => {
    const text = mrzText.trim();
    if (!text) return;

    // Tentative de parse MRZ côté frontend d'abord (rapide)
    const local = parseMrzJs(text);
    if (local) {
      toast.success("MRZ lu avec succès");
      onResult(local);
      onClose();
      return;
    }

    // Sinon envoyer au backend
    setLoading(true);
    try {
      const { data } = await api.post("/api/scan/mrz-text", { text });
      toast.success("Document lu avec succès");
      onResult(data);
      onClose();
    } catch (err) {
      toast.error(err.response?.data?.detail || "MRZ non reconnu");
    } finally {
      setLoading(false);
    }
  };

  // Détecter automatiquement une saisie complète (MRZ / barcode USB)
  const handleTextChange = (e) => {
    const v = e.target.value;
    setMrzText(v);
    // Auto-submit si ressemble à MRZ complet (2 ou 3 lignes de 30/44 chars)
    const lines = v.split(/[\n\r]+/).map(l => l.trim().replace(/[^A-Z0-9<]/gi, "").toUpperCase());
    const valid = lines.filter(l => l.length >= 28);
    if (valid.length >= 2) {
      setTimeout(() => handleMrzText(), 300);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" style={{ maxWidth: 520 }} onClick={e => e.stopPropagation()}>
        <h3 style={{ marginBottom: 16 }}>Scanner un document</h3>

        {/* Onglets de mode */}
        <div style={{ display: "flex", gap: 6, marginBottom: 20 }}>
          {MODES.map(m => (
            <button key={m.id}
              className={`btn btn-sm ${mode === m.id ? "btn-primary" : "btn-outline"}`}
              style={{ flex: 1, flexDirection: "column", padding: "8px 4px", lineHeight: 1.3 }}
              onClick={() => setMode(m.id)}>
              <span style={{ fontSize: 14 }}>{m.label}</span>
              <span style={{ fontSize: 10, opacity: 0.7 }}>{m.desc}</span>
            </button>
          ))}
        </div>

        {/* MODE : Fichier / Scanner USB */}
        {mode === "file" && (
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <div style={{ fontSize: 48, marginBottom: 12 }}>📄</div>
            <p style={{ color: "var(--muted)", marginBottom: 16, fontSize: 13 }}>
              Scannez votre document avec votre scanner, puis sélectionnez le fichier.
              <br />Formats acceptés : JPG, PNG, PDF (première page)
            </p>
            <button className="btn btn-primary"
              onClick={() => fileRef.current?.click()} disabled={loading}>
              {loading ? "Analyse en cours…" : "Choisir l'image scannée"}
            </button>
            <input ref={fileRef} type="file" accept="image/*,.pdf"
              style={{ display: "none" }} onChange={handleFile} />
          </div>
        )}

        {/* MODE : Webcam */}
        {mode === "camera" && (
          <div style={{ textAlign: "center" }}>
            <video ref={videoRef} autoPlay playsInline muted
              style={{ width: "100%", maxHeight: 280, background: "#000", borderRadius: 8, objectFit: "cover" }} />
            <canvas ref={canvasRef} style={{ display: "none" }} />
            <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 12 }}>
              <button className="btn btn-primary" onClick={captureCamera} disabled={loading || !camStream}>
                {loading ? "Analyse…" : "📷 Capturer le document"}
              </button>
            </div>
            <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 8 }}>
              Placez le document bien à plat, assurez-vous que le texte est net
            </p>
          </div>
        )}

        {/* MODE : Texte / Pistolet / MRZ reader */}
        {mode === "text" && (
          <div>
            <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 10 }}>
              Cliquez dans la zone ci-dessous, puis passez votre scanner USB ou
              lecteur MRZ — le texte sera automatiquement saisi et analysé.
            </p>
            <textarea ref={textRef}
              className="form-control"
              style={{ fontFamily: "monospace", fontSize: 13, height: 100,
                       letterSpacing: 1, background: "#0d1117", color: "#e6edf3" }}
              placeholder={"Passez votre scanner ici…\nEx: P<HTIJEAN<<PIERRE<<<<<<<<<<<<<<<<<<<<<\nA12345678HTI9001014M2512315<<<<<<<<<<<<<<0"}
              value={mrzText}
              onChange={handleTextChange}
              autoComplete="off"
              spellCheck={false}
            />
            <button className="btn btn-primary" style={{ marginTop: 10, width: "100%" }}
              onClick={handleMrzText} disabled={loading || !mrzText.trim()}>
              {loading ? "Analyse…" : "Analyser le texte"}
            </button>
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
          <button className="btn btn-outline btn-sm" onClick={onClose}>Fermer</button>
        </div>
      </div>
    </div>
  );
}


// ── Parser MRZ côté navigateur (pas besoin du backend) ───────────────────

function cleanMrz(s) { return s.replace(/[^A-Z0-9<]/gi, "").toUpperCase(); }

function parseDate(s, isBirth) {
  if (!s || s.length < 6) return "";
  const yy = parseInt(s.slice(0, 2)), mm = parseInt(s.slice(2, 4)), dd = parseInt(s.slice(4, 6));
  const year = (isBirth && yy > 30 ? 1900 : 2000) + yy;
  return `${year}-${String(mm).padStart(2, "0")}-${String(dd).padStart(2, "0")}`;
}

function fmt(s) { return s.replace(/<+/g, " ").trim().replace(/\b\w/g, c => c.toUpperCase()); }

function parseTD3(l1, l2) {
  const country = l1.slice(2, 5).replace(/<+/g, "");
  const [surnameRaw, givenRaw = ""] = l1.slice(5).split("<<");
  return {
    nom: fmt(surnameRaw),
    prenom: fmt(givenRaw),
    numero_document: l2.slice(0, 9).replace(/<+/g, ""),
    type_document: "PASSEPORT",
    nationalite: l2.slice(10, 13).replace(/<+/g, "") || country,
    date_naissance: parseDate(l2.slice(13, 19), true),
    date_expiration: parseDate(l2.slice(21, 27), false),
  };
}

function parseTD1(l1, l2, l3) {
  const [surnameRaw, givenRaw = ""] = l3.split("<<");
  return {
    nom: fmt(surnameRaw),
    prenom: fmt(givenRaw),
    numero_document: l1.slice(5, 14).replace(/<+/g, ""),
    type_document: "CNI",
    nationalite: l2.slice(15, 18).replace(/<+/g, ""),
    date_naissance: parseDate(l2.slice(0, 6), true),
    date_expiration: parseDate(l2.slice(8, 14), false),
  };
}

export function parseMrzJs(text) {
  const lines = text.split(/[\n\r\t|;]+/)
    .map(l => cleanMrz(l))
    .filter(l => l.length >= 28);

  const td3 = lines.filter(l => l.length === 44);
  if (td3.length >= 2) return parseTD3(td3[0], td3[1]);

  const td1 = lines.filter(l => l.length === 30);
  if (td1.length >= 3) return parseTD1(td1[0], td1[1], td1[2]);

  return null;
}
