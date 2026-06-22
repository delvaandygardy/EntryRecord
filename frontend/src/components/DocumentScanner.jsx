import { useRef, useState, useEffect } from "react";
import { createWorker } from "tesseract.js";
import api from "../api";
import toast from "react-hot-toast";

const MODES = [
  { id: "file",   icon: "📁", label: "Fichier / Scanner", desc: "Image JPG/PNG" },
  { id: "camera", icon: "📷", label: "Webcam",            desc: "Photo du document" },
  { id: "text",   icon: "⌨️",  label: "Pistolet / MRZ",   desc: "Lecteur USB ou saisie" },
  { id: "manual", icon: "✏️",  label: "Saisie manuelle",  desc: "Remplir directement" },
];

const BLANK_MANUAL = {
  nom: "", prenom: "", numero_document: "", type_document: "CNI",
  date_naissance: "", nationalite: "HTI", date_expiration: "",
};

function preprocessImage(source) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement("canvas");
      const scale = Math.min(1, 2400 / Math.max(img.width, img.height));
      canvas.width  = img.width  * scale;
      canvas.height = img.height * scale;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      const id = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const d = id.data;
      for (let i = 0; i < d.length; i += 4) {
        const gray = 0.299 * d[i] + 0.587 * d[i+1] + 0.114 * d[i+2];
        const c = Math.min(255, Math.max(0, (gray - 50) * 1.4));
        d[i] = d[i+1] = d[i+2] = c;
      }
      ctx.putImageData(id, 0, 0);
      canvas.toBlob(resolve, "image/jpeg", 0.92);
    };
    img.onerror = () => resolve(source);
    if (source instanceof Blob) img.src = URL.createObjectURL(source);
    else img.src = source;
  });
}

// Extrait des champs à partir de texte libre (CNI haïtienne, permis…)
function extractFromFreeText(text) {
  const lines = (text || "").split(/[\n\r]+/).map(l => l.trim()).filter(Boolean);
  let nom = "", prenom = "", numero_document = "", date_naissance = "";

  for (const line of lines) {
    const up = line.toUpperCase();

    // NOM
    const nomM = up.match(/\bNOM\b[:\s]+([A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ -]+)/);
    if (nomM && !nom) nom = nomM[1].trim();

    // PRÉNOM
    const prenomM = up.match(/\bPR[ÉE]NOM\b[:\s]+([A-ZÀÂÄÉÈÊËÎÏÔÖÙÛÜ -]+)/);
    if (prenomM && !prenom) prenom = prenomM[1].trim();

    // Date format JJ/MM/AAAA ou AAAA-MM-JJ
    if (!date_naissance) {
      const dm = line.match(/(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})/);
      if (dm) {
        let [, a, b, c] = dm;
        if (c.length === 2) c = (parseInt(c) > 30 ? "19" : "20") + c;
        if (parseInt(c) > 1900 && parseInt(a) <= 31 && parseInt(b) <= 12) {
          date_naissance = `${c}-${b.padStart(2,"0")}-${a.padStart(2,"0")}`;
        }
      }
    }

    // Numéro CIN haïtien : séquence de chiffres 6-15 (ou format NNN-NNN-NNNNN)
    if (!numero_document) {
      const cinM = line.match(/\b(\d[\d\- ]{5,14}\d)\b/);
      if (cinM) numero_document = cinM[1].replace(/[\- ]/g, "");
    }
  }

  return { nom, prenom, numero_document, date_naissance };
}

export default function DocumentScanner({ onResult, onClose }) {
  const [mode, setMode] = useState("file");
  const [status, setStatus] = useState("");
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [camStream, setCamStream] = useState(null);
  const [mrzText, setMrzText] = useState("");
  const [preview, setPreview] = useState(null);
  const [ocrFailed, setOcrFailed] = useState(false);
  const [manual, setManual] = useState(BLANK_MANUAL);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const fileRef  = useRef(null);
  const textRef  = useRef(null);

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
    setOcrFailed(false);
    // eslint-disable-next-line
  }, [mode]);

  useEffect(() => () => camStream?.getTracks().forEach(t => t.stop()), [camStream]);

  // ── OCR ──────────────────────────────────────────────────────────────────────
  const runOCR = async (imageSource) => {
    setBusy(true);
    setOcrFailed(false);
    setProgress(0);
    setStatus("Prétraitement image…");

    let worker;
    try {
      const processed = await preprocessImage(imageSource);

      worker = await createWorker("eng+fra", 1, {
        logger: m => {
          if (m.status === "recognizing text") {
            setProgress(Math.round(m.progress * 100));
            setStatus(`OCR : ${Math.round(m.progress * 100)}%`);
          } else {
            setStatus(m.status);
          }
        },
      });

      // Passe 1 : MRZ strict (PSM 6)
      await worker.setParameters({
        tessedit_char_whitelist: "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<",
        tessedit_pageseg_mode:   "6",
      });
      setStatus("Lecture MRZ…");
      let { data: { text: t1 } } = await worker.recognize(processed || imageSource);
      let result = parseMrzJs(t1);

      // Passe 2 : MRZ PSM 11 (texte épars)
      if (!result || (!result.nom && !result.numero_document)) {
        await worker.setParameters({ tessedit_pageseg_mode: "11" });
        const { data: { text: t2 } } = await worker.recognize(processed || imageSource);
        result = parseMrzJs(t2);
      }

      if (result && (result.nom || result.numero_document)) {
        toast.success("Document lu avec succès");
        onResult(result);
        onClose();
        return;
      }

      // Passe 3 : texte libre — CNI / permis sans MRZ
      setStatus("Lecture texte libre…");
      await worker.setParameters({
        tessedit_char_whitelist: "",   // pas de filtre
        tessedit_pageseg_mode:   "3",  // page entière
      });
      const { data: { text: t3 } } = await worker.recognize(processed || imageSource);
      const extracted = extractFromFreeText(t3);
      const hasData = extracted.nom || extracted.prenom || extracted.numero_document;
      if (hasData) {
        setManual({ ...BLANK_MANUAL, ...extracted });
        toast("Texte extrait — vérifiez et complétez", { icon: "📝", duration: 4000 });
      }

      // Fallback barcode backend
      setStatus("Recherche codes-barres…");
      const bcResult = await tryBackendBarcode(processed || imageSource);
      if (!bcResult) {
        setOcrFailed(true);
        setStatus("");
        if (!hasData) {
          toast("Lecture automatique impossible — saisissez manuellement", { icon: "⚠️", duration: 5000 });
        }
      }
    } catch (err) {
      toast.error("OCR échoué : " + (err.message || "erreur inconnue"));
      setStatus("");
      setOcrFailed(true);
    } finally {
      await worker?.terminate();
      setBusy(false);
      setProgress(0);
    }
  };

  const tryBackendBarcode = async (imageSource) => {
    try {
      let blob;
      if (imageSource instanceof Blob) blob = imageSource;
      else { const r = await fetch(imageSource); blob = await r.blob(); }
      const form = new FormData();
      form.append("file", blob, "doc.jpg");
      const { data } = await api.post("/api/scan/document", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Code-barres lu");
      onResult(data);
      onClose();
      return true;
    } catch { return false; }
  };

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setPreview(URL.createObjectURL(f));
    runOCR(f);
    e.target.value = "";
  };

  const captureCamera = () => {
    const video = videoRef.current, canvas = canvasRef.current;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth; canvas.height = video.videoHeight;
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
      toast.error("Format MRZ non reconnu");
      setOcrFailed(true);
    }
  };

  const handleTextChange = (e) => {
    const v = e.target.value;
    setMrzText(v);
    const lines = v.split(/[\n\r]+/).map(l => l.replace(/[^A-Z0-9<]/gi, "").toUpperCase()).filter(l => l.length >= 28);
    if (lines.length >= 2) setTimeout(() => {
      const result = parseMrzJs(v);
      if (result && (result.nom || result.numero_document)) {
        toast.success("MRZ lu automatiquement");
        onResult(result); onClose();
      }
    }, 400);
  };

  const submitManual = (e) => {
    e.preventDefault();
    if (!manual.nom && !manual.numero_document) {
      toast.error("Remplissez au moins le nom ou le numéro de document");
      return;
    }
    onResult(manual);
    onClose();
    toast.success("Informations saisies");
  };

  // Quand OCR échoue sur une image capturée → basculer en saisie visuelle
  const showVisualAssist = ocrFailed && preview && mode !== "text" && mode !== "manual";

  return (
    <div className="modal-overlay" onClick={!busy ? onClose : undefined}>
      <div className="modal" style={{ maxWidth: showVisualAssist ? 820 : 560, width: "97%" }}
        onClick={e => e.stopPropagation()}>
        <h3 style={{ marginBottom: 16 }}>Scanner un document d'identité</h3>

        {/* Onglets */}
        {!showVisualAssist && (
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
        )}

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

        {/* ── MODE : Saisie visuelle (OCR échoué + image disponible) ──────── */}
        {showVisualAssist && (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14,
              padding: "8px 12px", background: "#1c2128", borderRadius: 8, border: "1px solid var(--border)" }}>
              <span style={{ fontSize: 16 }}>📝</span>
              <span style={{ fontSize: 13, flex: 1 }}>
                Lecture automatique impossible — complétez les champs en vous aidant de la photo.
              </span>
              <button className="btn btn-outline btn-sm" onClick={() => { setOcrFailed(false); setPreview(null); }}>
                ↩ Recommencer
              </button>
            </div>

            <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
              {/* Image de référence */}
              <div style={{ flex: "0 0 240px" }}>
                <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 6 }}>Document capturé</div>
                <img src={preview} alt="Document"
                  style={{ width: "100%", borderRadius: 8, border: "1px solid var(--border)",
                    cursor: "zoom-in", objectFit: "contain", maxHeight: 320 }}
                  onClick={() => window.open(preview, "_blank")}
                />
                <div style={{ fontSize: 10, color: "var(--muted)", marginTop: 4, textAlign: "center" }}>
                  Cliquez pour agrandir
                </div>
              </div>

              {/* Formulaire */}
              <form onSubmit={submitManual} style={{ flex: 1 }}>
                <div className="form-row">
                  <div className="form-group"><label>Nom *</label>
                    <input className="form-control" autoFocus value={manual.nom}
                      onChange={e => setManual({...manual, nom: e.target.value})} /></div>
                  <div className="form-group"><label>Prénom</label>
                    <input className="form-control" value={manual.prenom}
                      onChange={e => setManual({...manual, prenom: e.target.value})} /></div>
                  <div className="form-group"><label>N° Document</label>
                    <input className="form-control" value={manual.numero_document}
                      onChange={e => setManual({...manual, numero_document: e.target.value})} /></div>
                  <div className="form-group"><label>Type</label>
                    <select className="form-select" value={manual.type_document}
                      onChange={e => setManual({...manual, type_document: e.target.value})}>
                      <option>CNI</option><option>PASSEPORT</option>
                      <option>PERMIS</option><option>TITRE_SEJOUR</option><option>AUTRE</option>
                    </select></div>
                  <div className="form-group"><label>Date naissance</label>
                    <input className="form-control" type="date" value={manual.date_naissance}
                      onChange={e => setManual({...manual, date_naissance: e.target.value})} /></div>
                  <div className="form-group"><label>Nationalité</label>
                    <input className="form-control" value={manual.nationalite}
                      onChange={e => setManual({...manual, nationalite: e.target.value})} /></div>
                </div>
                <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 8 }}>
                  <button type="button" className="btn btn-outline btn-sm" onClick={onClose}>Annuler</button>
                  <button type="submit" className="btn btn-primary">Utiliser ces infos</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ── MODES NORMAUX ─────────────────────────────────────────────── */}
        {!showVisualAssist && (
          <>
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
                  Sélectionnez une photo ou image scannée du document.<br/>
                  <strong>CNI / permis haïtien :</strong> scannez le verso (code-barres) si possible.
                </p>
                <button className="btn btn-primary" disabled={busy} onClick={() => fileRef.current?.click()}>
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
                  {preview && !busy && (
                    <button className="btn btn-outline btn-sm" style={{ marginLeft: 8 }}
                      onClick={() => setPreview(null)}>Reprendre</button>
                  )}
                </div>
                <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 8 }}>
                  Cadrez le document bien à plat et éclairé — tentez le verso pour CNI/permis
                </p>
              </div>
            )}

            {/* MODE : Texte / MRZ */}
            {mode === "text" && (
              <div>
                <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 10 }}>
                  Branchez votre lecteur MRZ ou pistolet USB. La détection est automatique.
                </p>
                <textarea ref={textRef} className="form-control"
                  style={{ fontFamily: "monospace", fontSize: 12, height: 90,
                    letterSpacing: 1, background: "#0d1117", color: "#58a6ff" }}
                  placeholder={"Passez votre scanner MRZ ici…\n\nPasseport (2×44) :\nP<HTINOMFAMILLE<<PRENOM<<<<<<<<<<<<<<<<<<<<\nA123456789HTI8502234M2712317<<<<<<<<<<<<<<8"}
                  value={mrzText} onChange={handleTextChange}
                  autoComplete="off" spellCheck={false}
                />
                <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                  <button className="btn btn-primary" style={{ flex: 1 }}
                    onClick={handleMrzSubmit} disabled={!mrzText.trim()}>Analyser</button>
                  <button className="btn btn-outline btn-sm" onClick={() => setMrzText("")}>Effacer</button>
                </div>
                <div style={{ fontSize: 11, color: "var(--muted)", marginTop: 10 }}>
                  Formats : Passeport ICAO TD3 (2×44), CNI TD1 (3×30)
                </div>
              </div>
            )}

            {/* MODE : Saisie manuelle */}
            {mode === "manual" && (
              <form onSubmit={submitManual}>
                <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 14 }}>
                  Remplissez les informations directement.
                </p>
                <div className="form-row">
                  <div className="form-group"><label>Nom *</label>
                    <input className="form-control" autoFocus value={manual.nom}
                      onChange={e => setManual({...manual, nom: e.target.value})} /></div>
                  <div className="form-group"><label>Prénom</label>
                    <input className="form-control" value={manual.prenom}
                      onChange={e => setManual({...manual, prenom: e.target.value})} /></div>
                  <div className="form-group"><label>N° Document</label>
                    <input className="form-control" value={manual.numero_document}
                      onChange={e => setManual({...manual, numero_document: e.target.value})} /></div>
                  <div className="form-group"><label>Type</label>
                    <select className="form-select" value={manual.type_document}
                      onChange={e => setManual({...manual, type_document: e.target.value})}>
                      <option>CNI</option><option>PASSEPORT</option>
                      <option>PERMIS</option><option>TITRE_SEJOUR</option><option>AUTRE</option>
                    </select></div>
                  <div className="form-group"><label>Date naissance</label>
                    <input className="form-control" type="date" value={manual.date_naissance}
                      onChange={e => setManual({...manual, date_naissance: e.target.value})} /></div>
                  <div className="form-group"><label>Nationalité</label>
                    <input className="form-control" value={manual.nationalite}
                      onChange={e => setManual({...manual, nationalite: e.target.value})} /></div>
                </div>
                <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 8 }}>
                  <button type="button" className="btn btn-outline btn-sm" onClick={onClose}>Annuler</button>
                  <button type="submit" className="btn btn-primary">Utiliser ces infos</button>
                </div>
              </form>
            )}

            {mode !== "manual" && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16 }}>
                <button className="btn btn-outline btn-sm" onClick={() => setMode("manual")}>
                  ✏️ Saisie manuelle
                </button>
                <button className="btn btn-outline btn-sm" disabled={busy} onClick={onClose}>Fermer</button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}


// ── Parser MRZ ────────────────────────────────────────────────────────────────

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
    nom: surname, prenom,
    numero_document: l2.slice(0, 9).replace(/<+/g, ""),
    type_document:   "PASSEPORT",
    nationalite:     l2.slice(10, 13).replace(/<+/g, "") || country,
    date_naissance:  parseDate(l2.slice(13, 19), true),
    date_expiration: parseDate(l2.slice(21, 27), false),
  };
}

function parseTD1(l1, l2, l3) {
  const nameStr = l3;
  const sepIdx  = nameStr.indexOf("<<");
  const surname  = fmt(sepIdx >= 0 ? nameStr.slice(0, sepIdx) : nameStr);
  const givenStr = sepIdx >= 0 ? nameStr.slice(sepIdx + 2) : "";
  const prenom   = fmt(givenStr.split("<<")[0]);
  return {
    nom: surname, prenom,
    numero_document: l1.slice(5, 14).replace(/<+/g, ""),
    type_document:   "CNI",
    nationalite:     l2.slice(15, 18).replace(/<+/g, ""),
    date_naissance:  parseDate(l2.slice(0, 6), true),
    date_expiration: parseDate(l2.slice(8, 14), false),
  };
}

export function parseMrzJs(text) {
  const lines = (text || "").split(/[\n\r\t|;]+/)
    .map(cleanLine).filter(l => l.length >= 28);

  const td3 = lines.filter(l => l.length === 44);
  if (td3.length >= 2) return parseTD3(td3[0], td3[1]);

  const td3loose = lines.filter(l => l.length >= 43 && l.length <= 45)
    .map(l => l.slice(0, 44).padEnd(44, "<"));
  if (td3loose.length >= 2) return parseTD3(td3loose[0], td3loose[1]);

  const td1 = lines.filter(l => l.length === 30);
  if (td1.length >= 3) return parseTD1(td1[0], td1[1], td1[2]);

  const td1loose = lines.filter(l => l.length >= 29 && l.length <= 31)
    .map(l => l.slice(0, 30).padEnd(30, "<"));
  if (td1loose.length >= 3) return parseTD1(td1loose[0], td1loose[1], td1loose[2]);

  return null;
}
