import { useRef, useState, useEffect } from "react";
import { createWorker } from "tesseract.js";
import api from "../api";
import toast from "react-hot-toast";

const MODES = [
  { id: "file",   icon: "📁", label: "Fichier / Scanner", desc: "Image scannée JPG/PNG" },
  { id: "camera", icon: "📷", label: "Webcam",            desc: "Photo du document" },
  { id: "text",   icon: "⌨️",  label: "Pistolet / MRZ",   desc: "Lecteur USB ou saisie" },
];

export default function DocumentScanner({ onResult, onClose }) {
  const [mode, setMode] = useState("file");
  const [status, setStatus] = useState("");
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [camStream, setCamStream] = useState(null);
  const [mrzText, setMrzText] = useState("");
  const [preview, setPreview] = useState(null);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileRef  = useRef(null);
  const textRef  = useRef(null);

  // Gestion caméra
  useEffect(() => {
    if (mode === "camera") {
      navigator.mediaDevices?.getUserMedia({ video: { facingMode: "environment" } })
        .then(s => { setCamStream(s); if (videoRef.current) videoRef.current.srcObject = s; })
        .catch(() => toast.error("Caméra inaccessible"));
    } else {
      camStream?.getTracks().forEach(t => t.stop());
      setCamStream(null);
    }
    if (mode === "text") setTimeout(() => textRef.current?.focus(), 80);
    // eslint-disable-next-line
  }, [mode]);

  useEffect(() => () => camStream?.getTracks().forEach(t => t.stop()), [camStream]);

  // ── OCR Tesseract.js (navigateur) ─────────────────────────────────
  const runOCR = async (imageSource) => {
    setBusy(true);
    setProgress(0);
    setStatus("Initialisation OCR…");

    let worker;
    try {
      worker = await createWorker("eng", 1, {
        logger: m => {
          if (m.status === "recognizing text") {
            setProgress(Math.round(m.progress * 100));
            setStatus(`OCR : ${Math.round(m.progress * 100)}%`);
          } else {
            setStatus(m.status);
          }
        },
      });

      await worker.setParameters({
        tessedit_char_whitelist: "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<",
        tessedit_pageseg_mode:   "6",
      });

      setStatus("Lecture du document…");
      const { data: { text } } = await worker.recognize(imageSource);

      setStatus("Analyse MRZ…");
      const result = parseMrzJs(text);

      if (result && (result.nom || result.numero_document)) {
        toast.success("Document lu avec succès");
        onResult(result);
        onClose();
      } else {
        // Fallback : envoyer l'image au backend (codes-barres)
        setStatus("Recherche de codes-barres…");
        await tryBackendBarcode(imageSource);
      }
    } catch (err) {
      toast.error("OCR échoué : " + (err.message || "erreur inconnue"));
      setStatus("");
    } finally {
      await worker?.terminate();
      setBusy(false);
      setProgress(0);
    }
  };

  // Fallback backend pour codes-barres (pyzbar)
  const tryBackendBarcode = async (imageSource) => {
    try {
      let blob;
      if (imageSource instanceof Blob) {
        blob = imageSource;
      } else {
        const resp = await fetch(imageSource);
        blob = await resp.blob();
      }
      const form = new FormData();
      form.append("file", blob, "doc.jpg");
      const { data } = await api.post("/api/scan/document", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Code-barres lu");
      onResult(data);
      onClose();
    } catch {
      toast.error("Aucune information lisible — vérifiez la qualité de l'image");
      setStatus("");
    }
  };

  // ── Handlers ──────────────────────────────────────────────────────
  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const url = URL.createObjectURL(f);
    setPreview(url);
    runOCR(f);
    e.target.value = "";
  };

  const captureCamera = () => {
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    canvas.width  = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    canvas.toBlob(blob => {
      setPreview(URL.createObjectURL(blob));
      runOCR(blob);
    }, "image/jpeg", 0.95);
  };

  const handleMrzSubmit = () => {
    const text = mrzText.trim();
    if (!text) return;
    const result = parseMrzJs(text);
    if (result && (result.nom || result.numero_document)) {
      toast.success("MRZ analysé");
      onResult(result);
      onClose();
    } else {
      toast.error("Format MRZ non reconnu — vérifiez les données");
    }
  };

  const handleTextChange = (e) => {
    const v = e.target.value;
    setMrzText(v);
    const lines = v.split(/[\n\r]+/).map(l => l.replace(/[^A-Z0-9<]/gi, "").toUpperCase()).filter(l => l.length >= 28);
    if (lines.length >= 2) setTimeout(() => handleMrzSubmitAuto(v), 400);
  };

  const handleMrzSubmitAuto = (text) => {
    const result = parseMrzJs(text);
    if (result && (result.nom || result.numero_document)) {
      toast.success("MRZ lu automatiquement");
      onResult(result);
      onClose();
    }
  };

  // ── Render ────────────────────────────────────────────────────────
  return (
    <div className="modal-overlay" onClick={!busy ? onClose : undefined}>
      <div className="modal" style={{ maxWidth: 540 }} onClick={e => e.stopPropagation()}>
        <h3 style={{ marginBottom: 16 }}>Scanner un document d'identité</h3>

        {/* Onglets */}
        <div style={{ display: "flex", gap: 6, marginBottom: 20 }}>
          {MODES.map(m => (
            <button key={m.id} disabled={busy}
              className={`btn btn-sm ${mode === m.id ? "btn-primary" : "btn-outline"}`}
              style={{ flex: 1, padding: "8px 4px" }}
              onClick={() => setMode(m.id)}>
              <div style={{ fontSize: 16 }}>{m.icon}</div>
              <div style={{ fontSize: 11, lineHeight: 1.3 }}>{m.label}</div>
              <div style={{ fontSize: 10, opacity: 0.6 }}>{m.desc}</div>
            </button>
          ))}
        </div>

        {/* Progress */}
        {busy && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ height: 4, background: "var(--border)", borderRadius: 2, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${progress || 10}%`, background: "var(--primary)",
                            transition: "width .3s", borderRadius: 2 }} />
            </div>
            <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 6, textAlign: "center" }}>{status}</div>
          </div>
        )}

        {/* MODE : Fichier */}
        {mode === "file" && (
          <div style={{ textAlign: "center", padding: "16px 0" }}>
            {preview ? (
              <img src={preview} alt="Document" style={{ maxWidth: "100%", maxHeight: 200,
                objectFit: "contain", border: "1px solid var(--border)", borderRadius: 6, marginBottom: 12 }} />
            ) : (
              <div style={{ fontSize: 52, marginBottom: 12 }}>📄</div>
            )}
            <p style={{ color: "var(--muted)", fontSize: 12, marginBottom: 14 }}>
              Placez le passeport ou la CNI sur votre scanner, numérisez-le puis<br/>
              sélectionnez le fichier image obtenu. L'OCR est fait dans le navigateur.
            </p>
            <button className="btn btn-primary" disabled={busy}
              onClick={() => fileRef.current?.click()}>
              {busy ? status || "Traitement…" : "📂 Choisir l'image"}
            </button>
            <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleFile} />
          </div>
        )}

        {/* MODE : Webcam */}
        {mode === "camera" && (
          <div style={{ textAlign: "center" }}>
            {!preview ? (
              <video ref={videoRef} autoPlay playsInline muted
                style={{ width: "100%", maxHeight: 260, background: "#000", borderRadius: 8, objectFit: "cover" }} />
            ) : (
              <img src={preview} alt="Capture" style={{ maxWidth: "100%", maxHeight: 260,
                objectFit: "contain", border: "1px solid var(--border)", borderRadius: 8 }} />
            )}
            <canvas ref={canvasRef} style={{ display: "none" }} />
            <div style={{ marginTop: 12 }}>
              <button className="btn btn-primary" disabled={busy || !camStream} onClick={captureCamera}>
                {busy ? status || "Analyse…" : "📷 Capturer"}
              </button>
            </div>
            <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 8 }}>
              Posez le document à plat, assurez-vous que la zone MRZ (lignes du bas) est bien visible
            </p>
          </div>
        )}

        {/* MODE : Texte / MRZ reader / pistolet */}
        {mode === "text" && (
          <div>
            <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 10 }}>
              Branchez votre lecteur MRZ ou pistolet USB. Cliquez dans la zone ci-dessous
              puis passez le scanner — la détection est automatique à la fin de la saisie.
            </p>
            <textarea ref={textRef}
              className="form-control"
              style={{ fontFamily: "monospace", fontSize: 12, height: 90,
                       letterSpacing: 1, background: "#0d1117", color: "#58a6ff" }}
              placeholder={"Passez votre scanner MRZ ici…\n\nExemple passeport (2 lignes de 44 car.) :\nP<HTINOMFAMILLE<<PRENOM<<<<<<<<<<<<<<<<<<<<\nA123456789HTI8502234M2712317<<<<<<<<<<<<<<8"}
              value={mrzText}
              onChange={handleTextChange}
              autoComplete="off" spellCheck={false}
            />
            <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
              <button className="btn btn-primary" style={{ flex: 1 }}
                onClick={handleMrzSubmit} disabled={!mrzText.trim()}>
                Analyser
              </button>
              <button className="btn btn-outline btn-sm" onClick={() => setMrzText("")}>
                Effacer
              </button>
            </div>
            <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 10 }}>
              Formats supportés : Passeport ICAO TD3 (2×44), CNI TD1 (3×30)
            </div>
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
          <button className="btn btn-outline btn-sm" disabled={busy} onClick={onClose}>Fermer</button>
        </div>
      </div>
    </div>
  );
}


// ── Parser MRZ JavaScript (aucune dépendance externe) ────────────────────

function cleanLine(s) { return (s || "").replace(/[^A-Z0-9<]/gi, "").toUpperCase(); }

function parseDate(s, isBirth) {
  if (!s || s.length < 6) return "";
  const yy = parseInt(s.slice(0, 2)), mm = parseInt(s.slice(2, 4)), dd = parseInt(s.slice(4, 6));
  if (isNaN(yy) || isNaN(mm) || isNaN(dd)) return "";
  const year = (isBirth && yy > 30 ? 1900 : 2000) + yy;
  return `${year}-${String(mm).padStart(2,"0")}-${String(dd).padStart(2,"0")}`;
}

function fmt(s) {
  return (s || "").replace(/<+/g, " ").trim()
    .toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
}

function parseTD3(l1, l2) {
  const country = l1.slice(2, 5).replace(/<+/g, "");
  const nameStr = l1.slice(5);
  const sepIdx  = nameStr.indexOf("<<");
  const surname  = fmt(sepIdx >= 0 ? nameStr.slice(0, sepIdx) : nameStr);
  const givenStr = sepIdx >= 0 ? nameStr.slice(sepIdx + 2) : "";
  const prenom   = fmt(givenStr.split("<<")[0]);
  return {
    nom:              surname,
    prenom:           prenom,
    numero_document:  l2.slice(0, 9).replace(/<+/g, ""),
    type_document:    "PASSEPORT",
    nationalite:      l2.slice(10, 13).replace(/<+/g, "") || country,
    date_naissance:   parseDate(l2.slice(13, 19), true),
    date_expiration:  parseDate(l2.slice(21, 27), false),
  };
}

function parseTD1(l1, l2, l3) {
  const nameStr  = l3;
  const sepIdx   = nameStr.indexOf("<<");
  const surname  = fmt(sepIdx >= 0 ? nameStr.slice(0, sepIdx) : nameStr);
  const givenStr = sepIdx >= 0 ? nameStr.slice(sepIdx + 2) : "";
  const prenom   = fmt(givenStr.split("<<")[0]);
  return {
    nom:              surname,
    prenom:           prenom,
    numero_document:  l1.slice(5, 14).replace(/<+/g, ""),
    type_document:    "CNI",
    nationalite:      l2.slice(15, 18).replace(/<+/g, ""),
    date_naissance:   parseDate(l2.slice(0, 6), true),
    date_expiration:  parseDate(l2.slice(8, 14), false),
  };
}

export function parseMrzJs(text) {
  const lines = (text || "").split(/[\n\r\t|;]+/)
    .map(cleanLine)
    .filter(l => l.length >= 28);

  // TD3 : 2 lignes de 44 chars exactement
  const td3 = lines.filter(l => l.length === 44);
  if (td3.length >= 2) return parseTD3(td3[0], td3[1]);

  // TD3 : tolérance ±1 char (erreurs de lecture scanner)
  const td3loose = lines.filter(l => l.length >= 43 && l.length <= 45)
    .map(l => l.slice(0, 44).padEnd(44, "<"));
  if (td3loose.length >= 2) return parseTD3(td3loose[0], td3loose[1]);

  // TD1 : 3 lignes de 30 chars
  const td1 = lines.filter(l => l.length === 30);
  if (td1.length >= 3) return parseTD1(td1[0], td1[1], td1[2]);

  // TD1 : tolérance ±1
  const td1loose = lines.filter(l => l.length >= 29 && l.length <= 31)
    .map(l => l.slice(0, 30).padEnd(30, "<"));
  if (td1loose.length >= 3) return parseTD1(td1loose[0], td1loose[1], td1loose[2]);

  return null;
}
