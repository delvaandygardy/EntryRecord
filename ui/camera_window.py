"""
Camera window for automatic license plate recognition.
Opens a live camera feed, detects plates, and saves to DB.
"""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageTk
import threading
import cv2
import time

from database.db_manager import insert_vehicule, get_points_entree
from modules.plate_recognition import CameraCapture, read_plate_from_image
from utils.helpers import cv2_to_photoimage, save_plate_image
from config import FRAME_WIDTH, FRAME_HEIGHT


class CameraWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Reconnaissance Automatique de Plaques")
        self.geometry("960x680")
        self.resizable(True, True)

        self._last_plates = {}   # plate -> timestamp
        self._running = True
        self._capture = None
        self._photo = None

        self._build_ui()
        self._start_camera()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        left = ctk.CTkFrame(self)
        left.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(left, text="Flux Caméra",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(0, 5))
        self.video_label = tk.Label(left, bg="black", width=640, height=480)
        self.video_label.pack()

        right = ctk.CTkFrame(self, width=280)
        right.pack(side="right", fill="y", padx=(0, 10), pady=10)
        right.pack_propagate(False)

        ctk.CTkLabel(right, text="Plaques Détectées",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))

        # Point d'entrée
        ctk.CTkLabel(right, text="Point d'Entrée:").pack(anchor="w", padx=10)
        self.entry_point_var = tk.StringVar(value="Principal")
        points = get_points_entree()
        self.entry_combo = ctk.CTkOptionMenu(right, variable=self.entry_point_var,
                                              values=points, width=240)
        self.entry_combo.pack(padx=10, pady=(0, 10))

        # Auto mode toggle
        self.auto_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(right, text="Enregistrement automatique",
                        variable=self.auto_var).pack(anchor="w", padx=10, pady=5)

        # Plate display
        self.plate_label = ctk.CTkLabel(right, text="---",
                                         font=ctk.CTkFont(size=28, weight="bold"),
                                         text_color="#1a73e8")
        self.plate_label.pack(pady=10)

        self.conf_label = ctk.CTkLabel(right, text="Confiance: ---", font=ctk.CTkFont(size=12))
        self.conf_label.pack()

        ctk.CTkButton(right, text="Enregistrer Manuellement",
                      command=self._manual_save, width=240).pack(pady=10, padx=10)

        # Manual entry
        ctk.CTkLabel(right, text="Saisie Manuelle:").pack(anchor="w", padx=10, pady=(10, 0))
        self.manual_entry = ctk.CTkEntry(right, placeholder_text="Ex: HT-1234-A",
                                          width=240, height=36)
        self.manual_entry.pack(padx=10)
        ctk.CTkButton(right, text="Ajouter Plaque", width=240,
                      fg_color="#34a853",
                      command=self._add_manual_plate).pack(pady=8, padx=10)

        # Log
        ctk.CTkLabel(right, text="Journal:").pack(anchor="w", padx=10)
        self.log_box = ctk.CTkTextbox(right, height=200, state="disabled",
                                       font=ctk.CTkFont(size=10))
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Status bar
        self.status_label = ctk.CTkLabel(self, text="Démarrage caméra…",
                                          text_color="gray", font=ctk.CTkFont(size=11))
        self.status_label.pack(side="bottom", pady=5)

        self._current_plate = None
        self._current_conf = 0.0

    def _start_camera(self):
        self._capture = CameraCapture(
            callback=self._on_plate_detected,
            on_frame=self._on_frame
        )
        threading.Thread(target=self._load_ocr, daemon=True).start()

    def _load_ocr(self):
        self.status_label.configure(text="Chargement du moteur OCR… (première fois: 30 sec)")
        try:
            from modules.plate_recognition import get_ocr_reader
            get_ocr_reader()
            self.status_label.configure(text="Caméra active — Recherche de plaques…")
            self._capture.start()
        except Exception as e:
            self.status_label.configure(text=f"Erreur OCR: {e}")

    def _on_frame(self, frame):
        if not self._running:
            return
        try:
            h, w = frame.shape[:2]
            max_w, max_h = 620, 450
            scale = min(max_w / w, max_h / h)
            nw, nh = int(w * scale), int(h * scale)
            photo = cv2_to_photoimage(frame, nw, nh)
            self._photo = photo
            self.video_label.configure(image=photo)
        except Exception:
            pass

    def _on_plate_detected(self, plate, confidence, frame):
        now = time.time()
        last = self._last_plates.get(plate, 0)
        if now - last < 5:
            return
        self._last_plates[plate] = now

        self._current_plate = plate
        self._current_conf = confidence

        self.plate_label.configure(text=plate)
        self.conf_label.configure(text=f"Confiance: {confidence:.1%}")
        self._log(f"Détecté: {plate} ({confidence:.1%})")

        if self.auto_var.get():
            self._save_plate(plate, confidence, frame)

    def _save_plate(self, plate, confidence, frame=None):
        img_path = None
        if frame is not None:
            try:
                img_path = save_plate_image(frame, plate)
            except Exception:
                pass
        point = self.entry_point_var.get()
        row_id = insert_vehicule(plate, confidence, img_path, point)
        if row_id:
            self._log(f"SAUVEGARDÉ: {plate} (ID={row_id})")
            self.plate_label.configure(text_color="#34a853")
            self.after(1500, lambda: self.plate_label.configure(text_color="#1a73e8"))
        else:
            self._log(f"Doublon ignoré: {plate}")

    def _manual_save(self):
        if self._current_plate:
            self._save_plate(self._current_plate, self._current_conf)

    def _add_manual_plate(self):
        text = self.manual_entry.get().strip().upper()
        if not text:
            return
        self._save_plate(text, 1.0)
        self.manual_entry.delete(0, "end")

    def _log(self, msg):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{ts}  {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _on_close(self):
        self._running = False
        if self._capture:
            self._capture.stop()
        self.destroy()
