"""
ANPR Service: Platerecognizer API (cloud) + EasyOCR (local fallback).
"""
import asyncio
import io
from typing import Optional
import httpx

PR_URL = "https://api.platerecognizer.com/v1/plate-reader/"


def _get_api_key() -> str:
    import os
    from dotenv import load_dotenv
    load_dotenv()
    return os.getenv("PLATERECOGNIZER_API_KEY", "")


async def _recognize_pr(image_bytes: bytes) -> list[dict]:
    """Call Platerecognizer cloud API."""
    api_key = _get_api_key()
    if not api_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                PR_URL,
                headers={"Authorization": f"Token {api_key}"},
                files={"upload": ("plate.jpg", image_bytes, "image/jpeg")},
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for r in data.get("results", []):
                plate = r.get("plate", "").upper().strip()
                score = float(r.get("score", 0))
                box = r.get("box", {})
                if plate and score >= 0.5:
                    results.append({
                        "plate": plate,
                        "confidence": round(score, 3),
                        "region": r.get("region", {}).get("code", ""),
                        "box": box,
                        "source": "platerecognizer",
                    })
            return results
    except Exception:
        return []


def _recognize_easyocr(frame) -> list[dict]:
    """Local EasyOCR fallback (synchronous)."""
    from modules.plate_recognition import read_plate_from_image
    detections = read_plate_from_image(frame)
    return [
        {"plate": p, "confidence": c, "region": "", "box": {}, "source": "easyocr"}
        for p, c, _ in detections
    ]


async def recognize_plate(frame, image_bytes: Optional[bytes] = None) -> list[dict]:
    """
    Try Platerecognizer API first, fallback to local EasyOCR.
    frame  : OpenCV BGR ndarray (always required for fallback)
    image_bytes : JPEG bytes of the frame (optional, used for API call)
    """
    if _get_api_key():
        if image_bytes is None:
            import cv2
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            image_bytes = buf.tobytes()
        results = await _recognize_pr(image_bytes)
        if results:
            return results

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _recognize_easyocr, frame)
