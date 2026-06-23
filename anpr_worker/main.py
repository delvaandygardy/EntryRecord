#!/usr/bin/env python3
"""
ANPR Worker — capture automatique des plaques d'immatriculation
Flux RTSP → détection mouvement → Plate Recognizer API → backend
"""

import cv2
import requests
import time
import os
import threading
import logging
import base64
from datetime import datetime, timedelta

import anthropic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ANPR] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("anpr")

# Correctif DNS pour QNAP : ajoute 8.8.8.8 APRÈS le DNS Docker interne (127.0.0.11)
# pour que les noms de containers ET les domaines externes fonctionnent
try:
    current = open("/etc/resolv.conf").read()
    if "8.8.8.8" not in current:
        with open("/etc/resolv.conf", "a") as f:
            f.write("nameserver 8.8.8.8\nnameserver 1.1.1.1\n")
except Exception:
    pass

RTSP_URL        = os.getenv("RTSP_URL",        "rtsp://admin:M0ntana06@172.20.25.100:554/live")
PR_TOKEN        = os.getenv("PLATERECOGNIZER_TOKEN") or os.getenv("PLATERECOGNIZER_API_KEY", "")
BACKEND_URL     = os.getenv("BACKEND_URL",     "http://backend:8000")
BACKEND_USER    = os.getenv("BACKEND_USER",    "admin")
BACKEND_PASS    = os.getenv("BACKEND_PASS",    "Admin1234!")
POINT_ENTREE    = os.getenv("POINT_ENTREE",    "Principal")
DEDUP_MINUTES   = int(os.getenv("DEDUP_MINUTES",   "1"))
MOTION_MIN      = int(os.getenv("MOTION_THRESHOLD", "400"))
CHECK_INTERVAL  = float(os.getenv("CHECK_INTERVAL", "0.05"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Déduplication : plaque → dernière détection
_seen: dict = {}
_token: str | None = None
_token_exp: datetime = datetime.min


# ─── Thread de lecture RTSP ──────────────────────────────────────────────────

class FrameGrabber(threading.Thread):
    """
    Lit le flux RTSP en continu dans un thread dédié.
    Sans ce thread, le buffer OpenCV s'accumule pendant les appels API
    (jusqu'à 15 s) et on finit par analyser des images périmées.
    """
    def __init__(self, url: str):
        super().__init__(daemon=True)
        self.url = url
        self._frame = None
        self._lock = threading.Lock()
        self.alive = False
        self._stop_evt = threading.Event()

    def run(self):
        cap = _open_rtsp(self.url)
        if not cap.isOpened():
            log.error("FrameGrabber : impossible d'ouvrir le flux")
            return
        self.alive = True
        while not self._stop_evt.is_set():
            ret, frame = cap.read()
            if not ret or frame is None:
                self.alive = False
                break
            with self._lock:
                self._frame = frame
        cap.release()
        self.alive = False

    def read(self):
        """Retourne la frame la plus récente."""
        with self._lock:
            if self._frame is None:
                return False, None
            return True, self._frame.copy()

    def stop(self):
        self._stop_evt.set()


def _open_rtsp(url: str):
    """Ouvre le flux RTSP avec les options FFmpeg basse-latence."""
    cap = cv2.VideoCapture()
    # Options pour minimiser la mise en tampon côté FFmpeg
    cap.open(
        url,
        cv2.CAP_FFMPEG,
        [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000,
            cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000,
        ],
    )
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


# ─── Auth backend ────────────────────────────────────────────────────────────

def _login() -> str | None:
    global _token, _token_exp
    for attempt in range(3):
        try:
            r = requests.post(
                f"{BACKEND_URL}/api/auth/login",
                json={"username": BACKEND_USER, "password": BACKEND_PASS},
                timeout=10,
            )
            if r.status_code == 200:
                _token = r.json()["access_token"]
                _token_exp = datetime.now() + timedelta(minutes=25)
                log.info("Token backend OK")
                return _token
        except Exception as e:
            log.warning(f"Login attempt {attempt+1}/3 failed: {e}")
        time.sleep(5)
    return None


def _token_ok() -> str | None:
    if _token is None or datetime.now() >= _token_exp:
        return _login()
    return _token


# ─── Claude vision — couleur véhicule ───────────────────────────────────────

def describe_vehicle(frame) -> str | None:
    """Envoie la frame à Claude Opus pour identifier la couleur dominante du véhicule."""
    if not ANTHROPIC_API_KEY:
        return None
    try:
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ok:
            return None
        img_b64 = base64.standard_b64encode(buf.tobytes()).decode("utf-8")
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Identifie la couleur principale de ce véhicule. "
                            "Réponds avec un seul mot en français "
                            "(ex: rouge, bleu, blanc, noir, gris, argent, vert, jaune, orange, marron, beige). "
                            "Si aucun véhicule n'est visible, réponds 'inconnu'."
                        ),
                    },
                ],
            }],
        )
        couleur = response.content[0].text.strip().lower()
        return couleur if len(couleur) <= 20 else None
    except Exception as e:
        log.warning(f"describe_vehicle(): {e}")
        return None


# ─── Plate Recognizer API ────────────────────────────────────────────────────

def recognize(frame) -> list:
    """Envoie la frame à l'API, retourne [(plaque, score, type_vehicule, region), ...]."""
    if not PR_TOKEN:
        log.error("PLATERECOGNIZER_TOKEN non défini — arrêt de la reconnaissance")
        return []
    try:
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ok:
            return []
        r = requests.post(
            "https://api.platerecognizer.com/v1/plate-reader/",
            headers={"Authorization": f"Token {PR_TOKEN}"},
            files={"upload": ("f.jpg", buf.tobytes(), "image/jpeg")},
            data={"regions": ""},
            timeout=15,
        )
        if r.status_code == 429:
            log.warning("Quota API Plate Recognizer dépassé")
            return []
        if r.status_code not in (200, 201):
            log.warning(f"API HTTP {r.status_code}: {r.text[:80]}")
            return []
        results = []
        for res in r.json().get("results", []):
            plate = res.get("plate", "").strip()
            if not plate or len(plate) < 2:
                continue
            type_v = res.get("vehicle", {}).get("type")
            region = res.get("region", {}).get("code")
            results.append((plate.upper(), float(res.get("score", 1.0)), type_v, region))
        return results
    except Exception as e:
        log.error(f"recognize(): {e}")
        return []


# ─── Backend save ────────────────────────────────────────────────────────────

def save_plate(plaque: str, confidence: float,
               type_vehicule: str | None = None,
               region_plaque: str | None = None,
               couleur_vehicule: str | None = None) -> tuple[bool, str]:
    """Retourne (succès, action) où action = 'ENTREE' | 'SORTIE'."""
    token = _token_ok()
    if not token:
        return False, ""
    body = {
        "plaque": plaque,
        "confidence": round(confidence, 3),
        "point_entree": POINT_ENTREE,
        "notes": "ANPR auto",
        "type_vehicule": type_vehicule,
        "region_plaque": region_plaque,
        "couleur_vehicule": couleur_vehicule,
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.post(f"{BACKEND_URL}/api/vehicules",
                          json=body, headers=headers, timeout=10)
        if r.status_code == 401:
            _login()
            headers["Authorization"] = f"Bearer {_token}"
            r = requests.post(f"{BACKEND_URL}/api/vehicules",
                              json=body, headers=headers, timeout=10)
        if r.status_code == 201:
            action = r.json().get("action", "ENTREE")
            return True, action
        return False, ""
    except Exception as e:
        log.error(f"save_plate(): {e}")
        return False, ""


# ─── Détection de mouvement ──────────────────────────────────────────────────

def motion_score(prev_gray, curr_gray) -> int:
    diff = cv2.absdiff(prev_gray, curr_gray)
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, k)
    return cv2.countNonZero(thresh)


# ─── Boucle principale ───────────────────────────────────────────────────────

def main():
    log.info("=== ANPR Worker démarrage ===")
    log.info(f"Caméra  : {RTSP_URL}")
    log.info(f"Backend : {BACKEND_URL}  Point : {POINT_ENTREE}")
    log.info(f"Dédup   : {DEDUP_MINUTES} min   Mouvement : >{MOTION_MIN}px")
    log.info(f"API     : {'PRÊTE' if PR_TOKEN else 'TOKEN MANQUANT !'}")

    log.info("Attente du backend...")
    for _ in range(24):
        try:
            if requests.get(f"{BACKEND_URL}/api/auth/login", timeout=3).status_code < 500:
                break
        except Exception:
            pass
        time.sleep(5)

    _login()

    while True:
        log.info("Connexion caméra (thread dédié)...")
        grabber = FrameGrabber(RTSP_URL)
        grabber.start()

        # Laisser le thread démarrer et vérifier la connexion
        time.sleep(2)
        if not grabber.alive:
            log.error("Impossible d'ouvrir le flux. Nouvelle tentative dans 15 s...")
            grabber.stop()
            time.sleep(15)
            continue

        log.info("Caméra connectée")
        prev_gray = None
        last_check = datetime.min

        while grabber.alive:
            time.sleep(0.05)  # 50 ms — polling léger, le grabber lit en arrière-plan

            now = datetime.now()
            if (now - last_check).total_seconds() < CHECK_INTERVAL:
                continue
            last_check = now

            ret, frame = grabber.read()
            if not ret or frame is None:
                continue

            small = cv2.resize(frame, (640, 360))
            gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            gray  = cv2.GaussianBlur(gray, (21, 21), 0)

            if prev_gray is None:
                prev_gray = gray
                continue

            score = motion_score(prev_gray, gray)
            prev_gray = gray

            if score < MOTION_MIN:
                continue

            log.info(f"Mouvement détecté ({score}px) → ANPR...")
            # L'appel API peut prendre plusieurs secondes ;
            # pendant ce temps le FrameGrabber continue de lire le flux.
            plates = recognize(frame)

            if not plates:
                log.info("Aucune plaque détectée")
                continue

            # Détection couleur une seule fois par événement de détection
            couleur = describe_vehicle(frame)
            if couleur:
                log.info(f"Couleur détectée : {couleur}")

            for plaque, conf, type_v, region in plates:
                last_seen = _seen.get(plaque)
                if last_seen and now - last_seen < timedelta(minutes=DEDUP_MINUTES):
                    log.info(f"Doublon ignoré : {plaque} (vu il y a {int((now-last_seen).total_seconds())}s)")
                    continue

                _seen[plaque] = now
                ok, action = save_plate(plaque, conf, type_v, region, couleur)
                if ok:
                    icon = "✓ ENTRÉE" if action == "ENTREE" else "✓ SORTIE"
                    extra = f"[{type_v}]" if type_v else ""
                    extra += f" {couleur}" if couleur else ""
                    log.info(f"{icon} : {plaque} ({conf:.0%}) {extra}".strip())
                else:
                    log.info(f"✗ Échec sauvegarde : {plaque} ({conf:.0%})")

        log.warning("Flux perdu — reconnexion dans 5 s...")
        grabber.stop()
        time.sleep(5)


if __name__ == "__main__":
    main()
