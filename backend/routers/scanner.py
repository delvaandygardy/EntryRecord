from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import StreamingResponse
import qrcode
import io
import re
import threading
import numpy as np
import cv2
from pyzbar.pyzbar import decode as pyzbar_decode
from backend.deps import get_db, get_current_user
from backend.schemas import ScanRequest
import psycopg2.extras

# ── OCR lazy init (EasyOCR heavy, load once) ──────────────────────────────
_ocr_lock = threading.Lock()
_ocr_reader = None

def _get_ocr():
    global _ocr_reader
    if _ocr_reader is None:
        with _ocr_lock:
            if _ocr_reader is None:
                import easyocr
                _ocr_reader = easyocr.Reader(["fr", "en"], gpu=False, verbose=False)
    return _ocr_reader


# ── MRZ helpers ────────────────────────────────────────────────────────────

def _parse_date(s: str, is_birth: bool = True) -> str | None:
    try:
        yy, mm, dd = int(s[:2]), int(s[2:4]), int(s[4:6])
        year = (1900 if is_birth and yy > 30 else 2000) + yy
        return f"{year:04d}-{mm:02d}-{dd:02d}"
    except Exception:
        return None


def _clean(s: str) -> str:
    return s.replace("<", " ").strip().title()


def _parse_td3(l1: str, l2: str) -> dict:
    """Passeport ICAO TD3 — 2 lignes × 44 caractères."""
    l1 = l1.ljust(44, "<")
    l2 = l2.ljust(44, "<")
    country = l1[2:5].replace("<", "")
    parts = l1[5:].split("<<", 1)
    surname = _clean(parts[0])
    prenom = _clean(parts[1]) if len(parts) > 1 else ""
    doc_no = l2[0:9].replace("<", "")
    nat = l2[10:13].replace("<", "") or country
    dob = _parse_date(l2[13:19], is_birth=True)
    exp = _parse_date(l2[21:27], is_birth=False)
    return {
        "nom": surname, "prenom": prenom,
        "numero_document": doc_no, "type_document": "PASSEPORT",
        "nationalite": nat, "date_naissance": dob, "date_expiration": exp,
    }


def _parse_td1(l1: str, l2: str, l3: str) -> dict:
    """Carte d'identité TD1 — 3 lignes × 30 caractères."""
    l1, l2, l3 = l1.ljust(30, "<"), l2.ljust(30, "<"), l3.ljust(30, "<")
    doc_no = l1[5:14].replace("<", "")
    dob = _parse_date(l2[0:6], is_birth=True)
    exp = _parse_date(l2[8:14], is_birth=False)
    nat = l2[15:18].replace("<", "")
    parts = l3.split("<<", 1)
    surname = _clean(parts[0])
    prenom = _clean(parts[1]) if len(parts) > 1 else ""
    return {
        "nom": surname, "prenom": prenom,
        "numero_document": doc_no, "type_document": "CNI",
        "nationalite": nat, "date_naissance": dob, "date_expiration": exp,
    }


def parse_mrz_text(text: str) -> dict | None:
    """Analyse un texte brut contenant des lignes MRZ."""
    lines = [re.sub(r"[^A-Z0-9<]", "", l.upper()) for l in re.split(r"[\n\r\t|;]+", text)]
    lines = [l for l in lines if len(l) >= 28]
    td3 = [l for l in lines if len(l) == 44]
    if len(td3) >= 2:
        return _parse_td3(td3[0], td3[1])
    td1 = [l for l in lines if len(l) == 30]
    if len(td1) >= 3:
        return _parse_td1(td1[0], td1[1], td1[2])
    return None

router = APIRouter(tags=["Scanner"])


def _qr_bytes(data: str) -> io.BytesIO:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


@router.get("/api/qr/employe/{eid}")
def qr_employe(eid: int, conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT matricule FROM employes WHERE id=%s", (eid,))
    emp = cur.fetchone()
    if not emp:
        raise HTTPException(404, "Employé introuvable")
    return StreamingResponse(_qr_bytes(f"HMT-EMP:{emp['matricule']}"), media_type="image/png")


@router.get("/api/qr/conducteur/{cid}")
def qr_conducteur(cid: int, conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id FROM conducteurs WHERE id=%s", (cid,))
    if not cur.fetchone():
        raise HTTPException(404, "Conducteur introuvable")
    return StreamingResponse(_qr_bytes(f"HMT-COND:{cid}"), media_type="image/png")


@router.get("/api/qr/pieton/{pid}")
def qr_pieton(pid: int, conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id FROM pietons WHERE id=%s", (pid,))
    if not cur.fetchone():
        raise HTTPException(404, "Piéton introuvable")
    return StreamingResponse(_qr_bytes(f"HMT-PIET:{pid}"), media_type="image/png")


@router.post("/api/scan")
def scan(body: ScanRequest, conn=Depends(get_db), _=Depends(get_current_user)):
    code = (body.code or "").strip()
    point = body.point_entree

    if code.startswith("HMT-EMP:"):
        return _badge_employe(code[8:], point, conn)
    elif code.startswith("HMT-COND:"):
        return _passage("conducteurs", int(code[9:]), point, conn)
    elif code.startswith("HMT-PIET:"):
        return _passage("pietons", int(code[9:]), point, conn)
    else:
        # Fallback : traiter comme matricule employé direct
        return _badge_employe(code, point, conn)


def _badge_employe(matricule: str, point: str, conn):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, nom, prenom, statut, poste FROM employes WHERE matricule=%s",
        (matricule.upper(),),
    )
    emp = cur.fetchone()
    if not emp:
        raise HTTPException(404, f"Matricule '{matricule}' introuvable")
    if emp["statut"] != "Actif":
        raise HTTPException(403, "Employé inactif")

    cur.execute(
        "SELECT type FROM presences WHERE employe_id=%s ORDER BY timestamp DESC LIMIT 1",
        (emp["id"],),
    )
    last = cur.fetchone()
    ptype = "SORTIE" if (last and last["type"] == "ENTREE") else "ENTREE"

    cur2 = conn.cursor()
    cur2.execute(
        "INSERT INTO presences (employe_id, type, methode, point_entree) VALUES (%s,%s,'SCAN',%s) RETURNING id",
        (emp["id"], ptype, point),
    )
    pid = cur2.fetchone()[0]
    conn.commit()
    return {
        "id": pid,
        "type": ptype,
        "categorie": "employe",
        "blacklist": False,
        "personne": {
            "nom": emp["nom"],
            "prenom": emp["prenom"],
            "ref": matricule.upper(),
            "poste": emp.get("poste"),
        },
    }


def _passage(table: str, record_id: int, point: str, conn):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(f"SELECT * FROM {table} WHERE id=%s", (record_id,))
    p = cur.fetchone()
    if not p:
        raise HTTPException(404, "Personne introuvable dans la base")

    alerte_blacklist = False
    if p.get("numero_document"):
        cur.execute(
            "SELECT motif FROM blacklist_personnes WHERE numero_document=%s AND actif=TRUE",
            (p["numero_document"],),
        )
        bl = cur.fetchone()
        if bl:
            alerte_blacklist = True
            cur2 = conn.cursor()
            cur2.execute(
                "INSERT INTO alertes (type, message, reference, severite) VALUES ('BLACKLIST_PERSONNE',%s,%s,'HAUTE')",
                (f"Personne en liste noire scannée: {bl['motif']}", p["numero_document"]),
            )
            conn.commit()

    cur2 = conn.cursor()
    cur2.execute(
        f"""INSERT INTO {table} (nom,prenom,numero_document,type_document,
            date_naissance,nationalite,date_expiration,point_entree)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (
            p["nom"], p["prenom"], p["numero_document"], p["type_document"],
            p["date_naissance"], p["nationalite"], p["date_expiration"], point,
        ),
    )
    new_id = cur2.fetchone()[0]
    conn.commit()

    cat = "conducteur" if table == "conducteurs" else "pieton"
    return {
        "id": new_id,
        "type": "ENTREE",
        "categorie": cat,
        "blacklist": alerte_blacklist,
        "personne": {
            "nom": p["nom"],
            "prenom": p["prenom"],
            "ref": p["numero_document"] or str(record_id),
            "poste": None,
        },
    }


# ── Document scan (image → champs) ────────────────────────────────────────

@router.post("/api/scan/document")
async def scan_document(file: UploadFile = File(...), _=Depends(get_current_user)):
    """Analyse une image de document et retourne les champs extraits."""
    data = await file.read()
    nparr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Image invalide ou format non supporté")

    # 1 — Codes-barres / QR (pyzbar)
    result = _scan_barcodes(img)
    if result:
        return result

    # 2 — MRZ via OCR (EasyOCR)
    result = _scan_mrz_ocr(img)
    if result:
        return result

    raise HTTPException(422, "Aucune information lisible — vérifiez la qualité de l'image")


@router.post("/api/scan/mrz-text")
async def scan_mrz_text(body: dict, _=Depends(get_current_user)):
    """Analyse du texte MRZ brut (lecteur MRZ / pistolet USB)."""
    text = body.get("text", "")
    result = parse_mrz_text(text)
    if not result:
        raise HTTPException(422, "Texte MRZ non reconnu")
    return result


def _scan_barcodes(img) -> dict | None:
    """Détecte et décode les codes-barres avec pyzbar."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    for processed in [gray, cv2.equalizeHist(gray)]:
        barcodes = pyzbar_decode(processed)
        for bc in barcodes:
            raw = bc.data.decode("utf-8", errors="ignore").strip()
            parsed = _parse_barcode_data(raw, bc.type)
            if parsed:
                return parsed
    return None


def _parse_barcode_data(raw: str, bc_type: str) -> dict | None:
    """Tente d'extraire des infos structurées d'un code-barres."""
    # QR code / HMT badge interne
    if raw.startswith("HMT-"):
        return None  # badge interne, pas un document

    # PDF417 typique (permis haïtien / AAMVA format)
    if bc_type in ("PDF417", "CODE128", "CODE39") and len(raw) > 10:
        return {
            "numero_document": raw[:20].strip(),
            "type_document": "PERMIS" if bc_type == "PDF417" else "CNI",
        }

    # Essai MRZ encodé dans un QR/barcode
    mrz = parse_mrz_text(raw)
    if mrz:
        return mrz

    return None


def _scan_mrz_ocr(img) -> dict | None:
    """Extrait les lignes MRZ d'une image via EasyOCR."""
    # Rogner la zone basse (MRZ en bas du document)
    h, w = img.shape[:2]
    zone = img[int(h * 0.55):, :]

    gray = cv2.cvtColor(zone, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    try:
        ocr = _get_ocr()
        results = ocr.readtext(thresh, allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789<")
        text = " \n ".join([r[1] for r in results if r[2] > 0.3])
        return parse_mrz_text(text)
    except Exception:
        return None
