import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio, json, threading, base64
from pathlib import Path


class _CamWorker:
    """Thread dédié par caméra — capture RTSP en continu, garde la dernière frame encodée."""
    def __init__(self, url: str):
        self.url = url
        self._frame: bytes | None = None
        self._lock = threading.Lock()
        self._viewers = 0
        self._thread: threading.Thread | None = None

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        import cv2
        os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")
        cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
        while self._viewers > 0:
            ret, frame = cap.read()
            if not ret:
                cap.release()
                cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
                continue
            h, w = frame.shape[:2]
            if w > 640:
                frame = cv2.resize(frame, (640, int(h * 640 / w)))
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 45])
            with self._lock:
                self._frame = buf.tobytes()
        cap.release()

    def get_frame(self) -> bytes | None:
        with self._lock:
            return self._frame

    def add_viewer(self):
        self._viewers += 1
        if self._viewers == 1:
            self.start()

    def remove_viewer(self):
        self._viewers = max(0, self._viewers - 1)

_cam_workers: dict[int, _CamWorker] = {}

from backend.routers import (auth_router, vehicules, personnes, employes,
                              blacklist, alertes, cameras, reports, admin, scanner,
                              points_acces)

app = FastAPI(title="Système d'Enregistrement Automatique", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(vehicules.router)
app.include_router(personnes.router)
app.include_router(employes.router)
app.include_router(blacklist.router)
app.include_router(alertes.router)
app.include_router(cameras.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(scanner.router)
app.include_router(points_acces.router)

# Run DB migrations on startup
@app.on_event("startup")
def startup():
    import psycopg2
    from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    from database.db_manager import init_db
    init_db()
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                             user=DB_USER, password=DB_PASSWORD)
    migration_sql = Path(__file__).parent.parent / "database" / "migrations" / "v2_new_features.sql"
    with open(migration_sql) as f:
        conn.cursor().execute(f.read())
    conn.commit()
    # Table points d'accès
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS points_acces (
            id   SERIAL PRIMARY KEY,
            nom  TEXT UNIQUE NOT NULL,
            actif BOOLEAN DEFAULT TRUE
        );
        INSERT INTO points_acces (nom) VALUES
            ('Principal'), ('Entrée Nord'), ('Entrée Sud')
        ON CONFLICT (nom) DO NOTHING;
    """)
    conn.commit()
    conn.close()
    print("✓ Base de données initialisée")


# ── WebSocket for real-time alerts ─────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, data: dict):
        msg = json.dumps(data)
        for ws in list(self.active):
            try:
                await ws.send_text(msg)
            except Exception:
                self.active.remove(ws)


manager = ConnectionManager()


@app.websocket("/ws/alertes")
async def ws_alertes(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws/camera/{camera_id}")
async def ws_camera_stream(websocket: WebSocket, camera_id: int):
    """Flux MJPEG encodé base64 depuis une caméra RTSP."""
    await websocket.accept()
    import psycopg2, psycopg2.extras, cv2, base64, asyncio
    from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                                user=DB_USER, password=DB_PASSWORD)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT url_rtsp FROM cameras_ip WHERE id=%s AND actif=TRUE", (camera_id,))
        cam = cur.fetchone()
        conn.close()
        if not cam:
            await websocket.close(code=4004, reason="Caméra introuvable")
            return
        rtsp_url = cam["url_rtsp"]
    except Exception:
        await websocket.close(code=4000)
        return

    if camera_id not in _cam_workers:
        _cam_workers[camera_id] = _CamWorker(rtsp_url)
    worker = _cam_workers[camera_id]
    worker.add_viewer()

    try:
        # Attendre la première frame max 10s
        for _ in range(50):
            if worker.get_frame():
                break
            await asyncio.sleep(0.2)
        else:
            await websocket.send_text(json.dumps({"error": "Impossible d'ouvrir le flux RTSP"}))
            return

        while True:
            frame_bytes = worker.get_frame()
            if frame_bytes:
                b64 = base64.b64encode(frame_bytes).decode()
                await websocket.send_text(json.dumps({"frame": b64}))
            await asyncio.sleep(0.2)  # 5 fps côté WebSocket
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        worker.remove_viewer()


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "2.0"}


# Serve captured images
import os as _os
_captures_dir = "/app/assets/captures"
_os.makedirs(_captures_dir, exist_ok=True)
app.mount("/captures", StaticFiles(directory=_captures_dir), name="captures")

# Serve React build
react_build = Path(__file__).parent.parent / "frontend" / "dist"
if react_build.exists():
    app.mount("/assets", StaticFiles(directory=str(react_build / "assets")), name="assets")

    @app.get("/favicon.svg", include_in_schema=False)
    def favicon():
        return FileResponse(str(react_build / "favicon.svg"))

    @app.get("/icons.svg", include_in_schema=False)
    def icons():
        return FileResponse(str(react_build / "icons.svg"))

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_react(full_path: str):
        return FileResponse(str(react_build / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
