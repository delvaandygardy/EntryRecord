from fastapi import APIRouter, Depends, BackgroundTasks
from backend.deps import get_db, get_current_user, require_role
from backend.schemas import CameraCreate
import psycopg2.extras
from datetime import datetime
import urllib.request, json as _json

MEDIAMTX_API = "http://mediamtx:9997"


def _mediamtx_add(cam_id: int, rtsp_url: str):
    """Enregistre un chemin HLS dans MediaMTX via son API REST."""
    path = f"camera{cam_id}"
    payload = _json.dumps({
        "source": rtsp_url,
        "sourceProtocol": "tcp",
        "sourceOnDemand": True,
        "sourceOnDemandStartTimeout": "10s",
        "sourceOnDemandCloseAfter": "60s",
    }).encode()
    try:
        req = urllib.request.Request(
            f"{MEDIAMTX_API}/v3/config/paths/add/{path}",
            data=payload, method="POST",
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # MediaMTX non disponible, on continue


def _mediamtx_remove(cam_id: int):
    path = f"camera{cam_id}"
    try:
        req = urllib.request.Request(
            f"{MEDIAMTX_API}/v3/config/paths/remove/{path}",
            method="DELETE",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass

router = APIRouter(prefix="/api/cameras", tags=["Caméras IP"])

# Active ANPR threads: camera_id -> thread
_active_streams: dict = {}


def _s(rows):
    for r in rows:
        for k in ("timestamp", "derniere_connexion"):
            if isinstance(r.get(k), datetime):
                r[k] = r[k].isoformat()
    return rows


@router.get("")
def list_cameras(conn=Depends(get_db), _=Depends(get_current_user)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM cameras_ip ORDER BY nom")
    rows = _s([dict(r) for r in cur.fetchall()])
    for r in rows:
        r["streaming"] = r["id"] in _active_streams
    return rows


@router.post("", status_code=201)
def add_camera(body: CameraCreate, conn=Depends(get_db),
               _=Depends(require_role("admin", "superviseur"))):
    cur = conn.cursor()
    cur.execute("""INSERT INTO cameras_ip (nom, url_rtsp, point_entree, actif)
                   VALUES (%s,%s,%s,%s) RETURNING id""",
                (body.nom, body.url_rtsp, body.point_entree, body.actif))
    cid = cur.fetchone()[0]
    conn.commit()
    if body.actif:
        _mediamtx_add(cid, body.url_rtsp)
    return {"id": cid}


@router.put("/{cid}")
def update_camera(cid: int, body: CameraCreate, conn=Depends(get_db),
                  _=Depends(require_role("admin", "superviseur"))):
    cur = conn.cursor()
    cur.execute("""UPDATE cameras_ip SET nom=%s,url_rtsp=%s,point_entree=%s,actif=%s
                   WHERE id=%s""",
                (body.nom, body.url_rtsp, body.point_entree, body.actif, cid))
    conn.commit()
    return {"ok": True}


@router.delete("/{cid}", status_code=204)
def delete_camera(cid: int, conn=Depends(get_db),
                  _=Depends(require_role("admin", "superviseur"))):
    _stop_stream(cid)
    _mediamtx_remove(cid)
    cur = conn.cursor()
    cur.execute("DELETE FROM cameras_ip WHERE id=%s", (cid,))
    conn.commit()


@router.post("/{cid}/start")
def start_stream(cid: int, background_tasks: BackgroundTasks,
                 conn=Depends(get_db), _=Depends(require_role("admin", "superviseur"))):
    if cid in _active_streams:
        return {"message": "Déjà actif"}
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM cameras_ip WHERE id=%s", (cid,))
    cam = cur.fetchone()
    if not cam:
        from fastapi import HTTPException
        raise HTTPException(404, "Caméra introuvable")
    background_tasks.add_task(_run_anpr_stream, cid, cam["url_rtsp"], cam["point_entree"])
    return {"message": f"Stream ANPR démarré pour {cam['nom']}"}


@router.post("/{cid}/stop")
def stop_stream(cid: int, _=Depends(require_role("admin", "superviseur"))):
    _stop_stream(cid)
    return {"message": "Stream arrêté"}


def _run_anpr_stream(camera_id: int, rtsp_url: str, point_entree: str):
    """Background ANPR: Platerecognizer API → fallback EasyOCR."""
    import sys, os, asyncio, cv2, time
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from database.db_manager import insert_vehicule, is_duplicate_vehicule

    # Boucle async pour pouvoir appeler le service ANPR async
    async def _loop():
        from backend.services.anpr_service import recognize_plate
        cap = cv2.VideoCapture(rtsp_url)
        last_detect: dict = {}
        try:
            while _active_streams.get(camera_id):
                ret, frame = cap.read()
                if not ret:
                    await asyncio.sleep(1)
                    cap.release()
                    cap = cv2.VideoCapture(rtsp_url)
                    continue
                detections = await recognize_plate(frame)
                for det in detections:
                    plate = det["plate"]
                    conf = det["confidence"]
                    now = time.time()
                    if now - last_detect.get(plate, 0) < 10:
                        continue
                    last_detect[plate] = now
                    insert_vehicule(plate, conf, None, point_entree)
        finally:
            cap.release()
            _active_streams.pop(camera_id, None)

    _active_streams[camera_id] = True
    asyncio.run(_loop())


def _stop_stream(camera_id: int):
    if camera_id in _active_streams:
        _active_streams[camera_id] = False


@router.post("/{cid}/capture")
async def capture_frame(cid: int, conn=Depends(get_db), _=Depends(get_current_user)):
    """Capture une frame depuis le flux HLS MediaMTX (HTTP, non-bloquant, <3s)."""
    import cv2, time, os, asyncio, tempfile, urllib.request
    from fastapi import HTTPException

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM cameras_ip WHERE id=%s", (cid,))
    cam = cur.fetchone()
    if not cam:
        raise HTTPException(404, "Caméra introuvable")

    def _capture_from_hls():
        import re, http.cookiejar
        hls_base = f"http://mediamtx:8888/camera{cid}"

        # Utiliser un cookie jar pour maintenir la session MediaMTX
        jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

        def _fetch(url, timeout=8):
            return opener.open(url, timeout=timeout).read().decode()

        def _fetch_bytes(url, timeout=10):
            return opener.open(url, timeout=timeout).read()

        def _non_comment_lines(text):
            return [l.strip() for l in text.splitlines() if l.strip() and not l.startswith('#')]

        # Niveau 1 : playlist maître
        master = _fetch(f"{hls_base}/index.m3u8")
        media_refs = _non_comment_lines(master)
        if not media_refs:
            raise RuntimeError("Aucune playlist HLS trouvée")

        media_ref = media_refs[0]
        media_url = media_ref if media_ref.startswith("http") else f"{hls_base}/{media_ref}"
        media_base = media_url.split("?")[0].rsplit("/", 1)[0]

        # Niveau 2 : playlist média
        media = _fetch(media_url)
        segments = _non_comment_lines(media)
        if not segments:
            raise RuntimeError("Aucun segment HLS disponible")

        # Récupérer le segment d'initialisation fMP4 (#EXT-X-MAP)
        init_data = b""
        map_match = re.search(r'#EXT-X-MAP:URI="([^"]+)"', media)
        if map_match:
            map_uri = map_match.group(1)
            map_url = map_uri if map_uri.startswith("http") else f"{media_base}/{map_uri}"
            init_data = _fetch_bytes(map_url)

        # Prendre l'avant-dernier segment complet
        seg_ref = segments[-2] if len(segments) >= 2 else segments[-1]
        seg_url = seg_ref if seg_ref.startswith("http") else f"{media_base}/{seg_ref}"
        seg_data = _fetch_bytes(seg_url)

        # Concaténer init + segment → fichier MP4 décodable
        combined = init_data + seg_data
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        try:
            tmp.write(combined)
            tmp.flush()
            tmp.close()
            cap = cv2.VideoCapture(tmp.name)
            ret, frame = cap.read()
            cap.release()
        finally:
            os.unlink(tmp.name)

        if not ret or frame is None:
            raise RuntimeError("Frame non décodable depuis le segment HLS")

        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return frame, buf.tobytes()

    loop = asyncio.get_event_loop()
    try:
        frame, image_bytes = await loop.run_in_executor(None, _capture_from_hls)
    except Exception as e:
        raise HTTPException(503, str(e))

    ts = int(time.time())
    save_dir = "/app/assets/captures"
    os.makedirs(save_dir, exist_ok=True)
    filename = f"capture_{cid}_{ts}.jpg"
    await loop.run_in_executor(None, lambda: cv2.imwrite(f"{save_dir}/{filename}", frame))

    return {
        "image_path": f"/captures/{filename}",
        "point_entree": cam["point_entree"],
        "camera_nom": cam["nom"],
    }


@router.post("/{cid}/anpr")
async def run_anpr(cid: int, body: dict, conn=Depends(get_db), _=Depends(get_current_user)):
    """Lance l'ANPR sur une image déjà capturée (chemin local)."""
    import cv2, asyncio
    from fastapi import HTTPException
    from backend.services.anpr_service import recognize_plate

    image_path = body.get("image_path", "")
    # /captures/captures/filename.jpg → /app/assets/captures/filename.jpg
    filename = image_path.rsplit("/", 1)[-1]
    full_path = f"/app/assets/captures/{filename}"

    def _load_and_encode():
        frame = cv2.imread(full_path)
        if frame is None:
            return None, None
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return frame, buf.tobytes()

    loop = asyncio.get_event_loop()
    frame, image_bytes = await loop.run_in_executor(None, _load_and_encode)
    if frame is None:
        raise HTTPException(404, "Image introuvable")

    plates = []
    anpr_error = None
    try:
        plates = await recognize_plate(frame, image_bytes)
    except Exception as e:
        anpr_error = str(e)

    return {"plates": plates, "anpr_error": anpr_error}
