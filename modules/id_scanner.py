"""
ID/Document scanner module.
Handles:
  - Barcode / QR code scanning via pyzbar (USB barcode scanner or webcam)
  - MRZ (Machine Readable Zone) parsing for passports and ID cards
  - USB HID keyboard-emulated scanners (most USB scanners)
"""
import re
import threading
import time
import queue


# ---------------------------------------------------------------------------
# MRZ parser (ISO 7501 TD1 / TD3)
# ---------------------------------------------------------------------------

MRZ_CLEANUP = re.compile(r"[^A-Z0-9<]")

def _mrz_clean(line):
    return MRZ_CLEANUP.sub("", line.upper().strip())


def parse_mrz(raw_text: str) -> dict:
    """Parse 2-line (TD3 passport) or 3-line (TD1 ID card) MRZ."""
    lines = [_mrz_clean(l) for l in raw_text.strip().splitlines() if l.strip()]
    lines = [l for l in lines if len(l) >= 30]

    if not lines:
        return {}

    result = {"raw_scan": raw_text, "type_document": "DOCUMENT"}

    try:
        if len(lines) >= 2 and len(lines[0]) == 44:
            # TD3 - Passport (2 × 44 chars)
            # Line 1: P<NATSurname<<Firstname<<<<<<<...  (pos 0-1: doc type, 2-4: country, 5-43: names)
            # Line 2: DocNum(9) Check Nation(3) DOB(6) Check Sex(1) Exp(6) Check PersonalNum(14) Check
            l1, l2 = lines[0], lines[1]
            result["type_document"] = "PASSEPORT"
            result["numero_document"] = l2[0:9].replace("<", "")
            result["nationalite"] = l2[10:13].replace("<", "")
            result["date_naissance"] = _format_mrz_date(l2[13:19])
            result["date_expiration"] = _format_mrz_date(l2[21:27])
            result.update(_split_mrz_name(l1[5:44]))

        elif len(lines) >= 3 and len(lines[0]) == 30:
            # TD1 - ID card (3 × 30 chars)
            l1, l2, l3 = lines[0], lines[1], lines[2]
            result["type_document"] = "CNI"
            result["numero_document"] = l1[5:14].replace("<", "")
            result["date_naissance"] = _format_mrz_date(l2[0:6])
            result["date_expiration"] = _format_mrz_date(l2[8:14])
            result["nationalite"] = l2[15:18].replace("<", "")
            result.update(_split_mrz_name(l3))

        elif len(lines) >= 2 and len(lines[0]) >= 30:
            # Generic fallback
            result["numero_document"] = lines[0][5:14].replace("<", "") if len(lines[0]) > 14 else ""
            result.update(_split_mrz_name(lines[-1]))
    except Exception:
        pass

    return result


def _format_mrz_date(s):
    if len(s) != 6 or not s.isdigit():
        return s
    yy, mm, dd = s[0:2], s[2:4], s[4:6]
    year = int(yy)
    full_year = 2000 + year if year <= 30 else 1900 + year
    return f"{dd}/{mm}/{full_year}"


def _split_mrz_name(name_field: str) -> dict:
    parts = name_field.split("<<")
    nom = parts[0].replace("<", " ").strip() if parts else ""
    prenom = parts[1].replace("<", " ").strip() if len(parts) > 1 else ""
    return {"nom": nom, "prenom": prenom}


# ---------------------------------------------------------------------------
# Barcode / QR scanner via pyzbar (webcam fallback)
# ---------------------------------------------------------------------------

def decode_barcodes_from_frame(frame):
    """Return list of decoded strings from a video frame."""
    try:
        from pyzbar.pyzbar import decode
        import cv2
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        decoded = decode(gray)
        return [d.data.decode("utf-8", errors="replace") for d in decoded]
    except ImportError:
        return []


# ---------------------------------------------------------------------------
# USB HID scanner (keyboard-emulated, reads lines from stdin-like source)
# ---------------------------------------------------------------------------

class HIDScanner:
    """
    Reads from a USB barcode/ID scanner that acts as a keyboard (HID mode).
    The scanner emits characters followed by Enter — we accumulate them.
    """

    def __init__(self, on_scan):
        self.on_scan = on_scan   # callback(raw_text: str)
        self._buffer = ""
        self._running = False
        self._thread = None
        self._queue = queue.Queue()

    def feed(self, char: str):
        """Feed a character (called from the Tkinter key-press handler)."""
        if char in ("\r", "\n"):
            data = self._buffer.strip()
            if data:
                self._queue.put(data)
                self._buffer = ""
        else:
            self._buffer += char

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _dispatch_loop(self):
        while self._running:
            try:
                data = self._queue.get(timeout=0.2)
                self.on_scan(data)
            except queue.Empty:
                continue


# ---------------------------------------------------------------------------
# Smart data router — decides which parser to use
# ---------------------------------------------------------------------------

def parse_scan_data(raw: str) -> dict:
    """
    Parse raw scanner output.
    Tries MRZ first, then barcode content heuristics.
    """
    lines = [l.strip() for l in raw.splitlines() if l.strip()]

    # Multi-line → likely MRZ
    if len(lines) >= 2 and any(len(l) >= 30 for l in lines):
        result = parse_mrz(raw)
        if result.get("numero_document"):
            return result

    # Single line barcode patterns
    raw_clean = raw.strip()

    # Haitian NIF / CIN barcode: digits only
    if re.match(r"^\d{8,16}$", raw_clean):
        return {
            "numero_document": raw_clean,
            "type_document": "CODE_BARRE",
            "raw_scan": raw,
        }

    # Structured barcode with field separators (common on AAMVA driver licenses)
    if raw_clean.startswith("@") or "\n" in raw_clean or "%" in raw_clean:
        return _parse_aamva(raw_clean)

    # Fallback
    return {"raw_scan": raw, "type_document": "INCONNU", "numero_document": raw_clean[:20]}


def _parse_aamva(raw: str) -> dict:
    """Parse AAMVA (North American) driver license barcode format."""
    result = {"raw_scan": raw, "type_document": "PERMIS"}
    patterns = {
        "DCS": "nom",
        "DCT": "prenom",
        "DAC": "prenom",
        "DBB": "date_naissance",
        "DBA": "date_expiration",
        "DAQ": "numero_document",
        "DCG": "nationalite",
    }
    for code, field in patterns.items():
        m = re.search(rf"{code}([^\n\r]+)", raw)
        if m:
            result[field] = m.group(1).strip()
    return result
