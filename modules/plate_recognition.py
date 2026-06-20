import cv2
import numpy as np
import re
import threading
import time
from config import (CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT,
                    PLATE_DETECT_INTERVAL, OCR_CONFIDENCE_THRESHOLD)

_ocr_reader = None
_ocr_lock = threading.Lock()


def get_ocr_reader():
    global _ocr_reader
    with _ocr_lock:
        if _ocr_reader is None:
            import easyocr
            _ocr_reader = easyocr.Reader(["fr", "en"], gpu=False, verbose=False)
    return _ocr_reader


def preprocess_plate_region(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    kernel = np.ones((1, 1), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    return thresh


def detect_plate_regions(frame):
    """Find candidate license plate regions in a frame."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    edged = cv2.Canny(gray, 30, 200)

    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:30]

    plate_regions = []
    for cnt in contours:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.018 * peri, True)
        if len(approx) == 4:
            x, y, w, h = cv2.boundingRect(approx)
            aspect = w / float(h)
            if 2.0 <= aspect <= 6.0 and w > 80 and h > 20:
                plate_regions.append((x, y, w, h))

    return plate_regions


def clean_plate_text(text):
    text = text.upper().strip()
    text = re.sub(r"[^A-Z0-9\-]", "", text)
    # Haitian plate format: typically AA 1234 or similar
    return text


def read_plate_from_image(frame):
    """Return list of (plate_text, confidence) tuples from frame."""
    results = []
    regions = detect_plate_regions(frame)

    if not regions:
        # Fall back to full-frame OCR on smaller region
        h, w = frame.shape[:2]
        regions = [(int(w * 0.1), int(h * 0.5), int(w * 0.8), int(h * 0.4))]

    reader = get_ocr_reader()
    for (x, y, w, h) in regions[:3]:
        roi = frame[y:y+h, x:x+w]
        if roi.size == 0:
            continue
        roi_resized = cv2.resize(roi, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        preprocessed = preprocess_plate_region(roi_resized)
        ocr_results = reader.readtext(preprocessed)
        for (_, text, conf) in ocr_results:
            cleaned = clean_plate_text(text)
            if conf >= OCR_CONFIDENCE_THRESHOLD and len(cleaned) >= 4:
                results.append((cleaned, round(conf, 3), (x, y, w, h)))

    return results


class CameraCapture:
    def __init__(self, callback, on_frame=None):
        self.callback = callback    # called with (plate_text, confidence, frame)
        self.on_frame = on_frame    # called with raw frame for preview
        self._running = False
        self._thread = None
        self._cap = None
        self._last_detect = 0

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._cap:
            self._cap.release()
            self._cap = None

    def _loop(self):
        self._cap = cv2.VideoCapture(CAMERA_INDEX)
        if not self._cap.isOpened():
            self._cap = cv2.VideoCapture(CAMERA_INDEX + 1)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            if self.on_frame:
                self.on_frame(frame.copy())

            now = time.time()
            if now - self._last_detect >= PLATE_DETECT_INTERVAL:
                self._last_detect = now
                detections = read_plate_from_image(frame)
                for (plate, conf, region) in detections:
                    annotated = frame.copy()
                    x, y, w, h = region
                    cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(annotated, plate, (x, y-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    self.callback(plate, conf, annotated)

            time.sleep(0.03)

        if self._cap:
            self._cap.release()
