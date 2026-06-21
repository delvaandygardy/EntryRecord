from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import qrcode
import io
from backend.deps import get_db, get_current_user
from backend.schemas import ScanRequest
import psycopg2.extras

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
