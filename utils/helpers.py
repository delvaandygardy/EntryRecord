import os
import re
from datetime import datetime
from config import ASSETS_DIR


def cv2_to_photoimage(frame, width=None, height=None):
    import cv2
    from PIL import Image, ImageTk
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb)
    if width and height:
        img = img.resize((width, height), Image.LANCZOS)
    return ImageTk.PhotoImage(img)


def save_plate_image(frame, plate_text, folder=None):
    import cv2
    if folder is None:
        folder = os.path.join(ASSETS_DIR, "plates")
    os.makedirs(folder, exist_ok=True)
    safe = re.sub(r"[^A-Z0-9]", "_", plate_text.upper())
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(folder, f"{safe}_{ts}.jpg")
    cv2.imwrite(path, frame)
    return path


def format_timestamp(ts_str):
    try:
        dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y  %H:%M:%S")
    except Exception:
        return ts_str


def truncate(text, max_len=25):
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len - 1] + "…"


def export_csv(rows, filepath, columns):
    import csv
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def generate_daily_report_pdf(stats, filepath):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("Rapport Journalier — Enregistrements", styles["Title"]))
        story.append(Spacer(1, 12))

        today = datetime.now().strftime("%d/%m/%Y")
        story.append(Paragraph(f"Date: {today}", styles["Normal"]))
        story.append(Spacer(1, 12))

        data = [
            ["Catégorie", "Aujourd'hui", "Total"],
            ["Véhicules", stats.get("vehicules_today", 0), stats.get("vehicules_total", 0)],
            ["Conducteurs", stats.get("conducteurs_today", 0), stats.get("conducteurs_total", 0)],
            ["Piétons", stats.get("pietons_today", 0), stats.get("pietons_total", 0)],
        ]
        table = Table(data, colWidths=[200, 100, 100])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a73e8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f3f4")]),
        ]))
        story.append(table)
        doc.build(story)
        return True
    except ImportError:
        return False
