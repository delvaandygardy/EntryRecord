#!/usr/bin/env python3
"""
ANPR Worker — capture automatique des plaques d'immatriculation
Flux RTSP → détection mouvement → Plate Recognizer API → backend
"""

import cv2
import requests
import time
import os
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ANPR] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("anpr")

# Correctif DNS pour QNAP (127.0.0.11 → 10.0.5.1 ne résout pas l'internet)
try:
    with open("/etc/resolv.conf", "w") as f:
        f.write("nameserver 8.8.8.8\nnameserver 1.1.1.1\n")
except Exception:
    pass

RTSP_URL        = os.getenv("RTSP_URL",        "rtsp://admin:M0ntana06@172.20.25.100:554/live")
PR_TOKEN        = os.getenv("PLATERECOGNIZER_TOKEN") or os.getenv("PLATERECOGNIZER_API_KEY", "")
BACKEND_URL     = os.getenv("BACKEND_URL",     "http://backend:8000")
BACKEND_USER    = os.getenv("BACKEND_USER",    "admin")
BACKEND_PASS    = os.getenv("BACKEND_PASS",    "Admin1234!")
POINT_ENTREE    = os.getenv("POINT_ENTREE",    "Principal")
DEDUP_MINUTES   = int(os.getenv("DEDUP_MINUTES",   "5"))
MOTION_MIN      = int(os.getenv("MOTION_THRESHOLD", "400"))
CHECK_INTERVAL  = float(os.getenv("CHECK_INTERVAL", "2.0"))  # secondes entre analyses

# Déduplication : plaque → dernière détection
_seen: dict = {}
_token: str | None = None
_token_exp: datetime = datetime.min


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


# ─── Plate Recognizer API ────────────────────────────────────────────────────

def recognize(frame) -> list:
    """Envoie la frame à l'API, retourne [(plaque, score), ...]."""
    if not PR_TOKEN:
        log.error("PLATERECOGNIZER_TOKEN non défini — arrêt de la reconnaissance")
        return []
    try:
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
        if not ok:
            return []
        r = requests.post(
            "https://api.platerecognizer.com/v1/plate-reader/",
            headers={"Authorization": f"Token {PR_TOKEN}"},
            files={"upload": ("f.jpg", buf.tobytes(), "image/jpeg")},
            data={"regions": ""},   # laisser vide = détection globale
            timeout=15,
        )
        if r.status_code == 429:
            log.warning("Quota API Plate Recognizer dépassé")
            return []
        if r.status_code not in (200, 201):
            log.warning(f"API HTTP {r.status_code}: {r.text[:80]}")
            return []
        return [
            (res["plate"].upper().strip(), float(res.get("score", 1.0)))
            for res in r.json().get("results", [])
            if res.get("plate") and len(res["plate"].strip()) >= 2
        ]
    except Exception as e:
        log.error(f"recognize(): {e}")
        return []


# ─── Backend save ────────────────────────────────────────────────────────────

def save_plate(plaque: str, confidence: float) -> bool:
    token = _token_ok()
    if not token:
        return False
    body = {
        "plaque": plaque,
        "confidence": round(confidence, 3),
        "point_entree": POINT_ENTREE,
        "notes": "ANPR auto",
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.post(f"{BACKEND_URL}/api/vehicules",
                          json=body, headers=headers, timeout=10)
        if r.status_code == 401:
            # Token expiré — renouveler et réessayer
            _login()
            headers["Authorization"] = f"Bearer {_token}"
            r = requests.post(f"{BACKEND_URL}/api/vehicules",
                              json=body, headers=headers, timeout=10)
        return r.status_code == 201
    except Exception as e:
        log.error(f"save_plate(): {e}")
        return False


# ─── Détection de mouvement ──────────────────────────────────────────────────

def motion_score(prev_gray, curr_gray) -> int:
    diff = cv2.absdiff(prev_gray, curr_gray)
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, k)
    return cv2.countNonZero(thresh)


# ─── Boucle principale ───────────────────────────────────────────────────────

def open_rtsp(url: str):
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def main():
    log.info("=== ANPR Worker démarrage ===")
    log.info(f"Caméra  : {RTSP_URL}")
    log.info(f"Backend : {BACKEND_URL}  Point : {POINT_ENTREE}")
    log.info(f"Dédup   : {DEDUP_MINUTES} min   Mouvement : >{MOTION_MIN}px")
    log.info(f"API     : {'PRÊTE' if PR_TOKEN else 'TOKEN MANQUANT !'}")

    # Attendre le backend au démarrage
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
        log.info("Connexion caméra...")
        cap = open_rtsp(RTSP_URL)

        if not cap.isOpened():
            log.error("Impossible d'ouvrir le flux. Nouvelle tentative dans 15 s...")
            time.sleep(15)
            continue

        log.info("Caméra connectée")
        prev_gray = None
        last_check = datetime.min
        consecutive_errors = 0

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                consecutive_errors += 1
                if consecutive_errors > 5:
                    log.warning("Flux perdu — reconnexion...")
                    break
                time.sleep(1)
                continue
            consecutive_errors = 0

            now = datetime.now()
            if (now - last_check).total_seconds() < CHECK_INTERVAL:
                time.sleep(0.1)
                continue
            last_check = now

            # Réduire pour la détection de mouvement
            small = cv2.resize(frame, (640, 360))
            gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            gray  = cv2.GaussianBlur(gray, (21, 21), 0)

            if prev_gray is None:
                prev_gray = gray
                continue

            score = motion_score(prev_gray, gray)
            prev_gray = gray

            if score < MOTION_MIN:
                continue  # pas de mouvement significatif

            log.info(f"Mouvement détecté ({score}px) → ANPR...")
            plates = recognize(frame)

            if not plates:
                log.info("Aucune plaque détectée")
                continue

            for plaque, conf in plates:
                last_seen = _seen.get(plaque)
                if last_seen and now - last_seen < timedelta(minutes=DEDUP_MINUTES):
                    log.info(f"Doublon ignoré : {plaque} (vu il y a {int((now-last_seen).total_seconds())}s)")
                    continue

                _seen[plaque] = now
                ok = save_plate(plaque, conf)
                log.info(f"{'✓ Sauvegardé' if ok else '✗ Échec sauvegarde'} : {plaque} ({conf:.0%})")

        cap.release()
        time.sleep(5)


if __name__ == "__main__":
    main()
