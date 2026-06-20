"""
Scanner window for Conducteurs and Piétons.
Supports:
  1. USB HID scanners (keyboard-emulated) — most common
  2. Webcam-based barcode scanning via pyzbar
  3. Manual text entry (paste MRZ or barcode data)
"""
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import threading
import time

from database.db_manager import insert_conducteur, insert_pieton, get_points_entree
from modules.id_scanner import HIDScanner, parse_scan_data


class ScannerWindow(ctk.CTkToplevel):
    MODE_LABELS = {
        "conducteur": ("Scanner Conducteurs", "#34a853"),
        "pieton": ("Scanner Piétons", "#fbbc04"),
    }

    def __init__(self, parent, mode="pieton"):
        super().__init__(parent)
        self.mode = mode
        title, _ = self.MODE_LABELS.get(mode, ("Scanner", "#1a73e8"))
        self.title(title)
        self.geometry("820x660")
        self.resizable(True, True)

        self._hid = HIDScanner(on_scan=self._on_raw_scan)
        self._hid.start()
        self._build_ui()

        # Capture all keystrokes and feed to HID scanner
        self.bind("<Key>", self._on_keypress)
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        title_text, color = self.MODE_LABELS.get(self.mode, ("Scanner", "#1a73e8"))
        ctk.CTkLabel(self, text=title_text,
                     font=ctk.CTkFont(size=20, weight="bold"),
                     text_color=color).pack(pady=(15, 5))

        mode_desc = {
            "conducteur": "Scan du permis de conduire ou de la pièce d'identité du conducteur",
            "pieton": "Scan de la pièce d'identité (CNI, passeport, autre)",
        }
        ctk.CTkLabel(self, text=mode_desc.get(self.mode, ""),
                     font=ctk.CTkFont(size=12)).pack()

        # Scanner input area
        input_frame = ctk.CTkFrame(self)
        input_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(input_frame,
                     text="Coller ou scanner le code-barre / MRZ ici:",
                     font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(5, 2))
        self.raw_input = ctk.CTkTextbox(input_frame, height=80,
                                         font=ctk.CTkFont(size=11, family="Courier"))
        self.raw_input.pack(fill="x", padx=5, pady=(0, 5))

        btn_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=5)
        ctk.CTkButton(btn_row, text="Analyser", width=120, fg_color=color,
                      command=self._parse_manual).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_row, text="Effacer", width=90,
                      fg_color="transparent", border_width=1,
                      command=lambda: self.raw_input.delete("1.0", "end")).pack(side="left")
        ctk.CTkLabel(btn_row,
                     text="(Le scanner USB remplit ce champ automatiquement)",
                     font=ctk.CTkFont(size=10), text_color="gray").pack(side="left", padx=10)

        # Parsed fields
        fields_frame = ctk.CTkFrame(self)
        fields_frame.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(fields_frame, text="Informations Extraites",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(8, 5))

        field_defs = [
            ("Nom", "nom"), ("Prénom", "prenom"),
            ("N° Document", "numero_document"), ("Type", "type_document"),
            ("Date Naissance", "date_naissance"), ("Nationalité", "nationalite"),
            ("Date Expiration", "date_expiration"), ("", ""),
        ]
        self._field_vars = {}
        for i, (label, key) in enumerate(field_defs):
            row, col = divmod(i, 2)
            row += 1
            if label:
                ctk.CTkLabel(fields_frame, text=label + ":",
                             font=ctk.CTkFont(size=12)).grid(
                    row=row, column=col*2, sticky="e", padx=(10, 5), pady=3)
                var = tk.StringVar()
                entry = ctk.CTkEntry(fields_frame, textvariable=var, width=220, height=32)
                entry.grid(row=row, column=col*2+1, sticky="w", padx=(0, 15), pady=3)
                self._field_vars[key] = var

        # Point d'entrée
        ctk.CTkLabel(fields_frame, text="Point d'Entrée:",
                     font=ctk.CTkFont(size=12)).grid(
            row=len(field_defs)//2+1, column=0, sticky="e", padx=(10, 5), pady=3)
        self.entry_point_var = tk.StringVar(value="Principal")
        points = get_points_entree()
        ctk.CTkOptionMenu(fields_frame, variable=self.entry_point_var,
                           values=points, width=220).grid(
            row=len(field_defs)//2+1, column=1, sticky="w")

        # Save button
        ctk.CTkButton(self, text="Enregistrer",
                      width=200, height=44,
                      font=ctk.CTkFont(size=14, weight="bold"),
                      fg_color=color,
                      command=self._save_record).pack(pady=10)

        # Log
        ctk.CTkLabel(self, text="Journal:",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20)
        self.log_box = ctk.CTkTextbox(self, height=120, state="disabled",
                                       font=ctk.CTkFont(size=10))
        self.log_box.pack(fill="x", padx=20, pady=(0, 10))

        # Status indicator
        self.status_label = ctk.CTkLabel(self, text="En attente du scanner…",
                                          text_color="gray", font=ctk.CTkFont(size=11))
        self.status_label.pack(pady=(0, 10))

    def _on_keypress(self, event):
        char = event.char
        if char:
            self._hid.feed(char)
        elif event.keysym in ("Return", "KP_Enter"):
            self._hid.feed("\n")

    def _on_raw_scan(self, raw: str):
        self.raw_input.delete("1.0", "end")
        self.raw_input.insert("end", raw)
        self._process_scan(raw)

    def _parse_manual(self):
        raw = self.raw_input.get("1.0", "end").strip()
        if raw:
            self._process_scan(raw)

    def _process_scan(self, raw: str):
        self.status_label.configure(text="Analyse en cours…", text_color="#fbbc04")
        data = parse_scan_data(raw)
        for key, var in self._field_vars.items():
            var.set(data.get(key, ""))
        self._log(f"Document analysé: {data.get('type_document','?')} — {data.get('numero_document','')}")
        self.status_label.configure(text="Document analysé. Vérifiez et enregistrez.",
                                     text_color="#34a853")

    def _save_record(self):
        data = {k: v.get().strip() for k, v in self._field_vars.items()}
        data["raw_scan"] = self.raw_input.get("1.0", "end").strip()
        data["point_entree"] = self.entry_point_var.get()

        if not data.get("numero_document") and not data.get("nom"):
            messagebox.showwarning("Données manquantes",
                                   "Veuillez scanner ou saisir un document d'identité.")
            return

        if self.mode == "conducteur":
            row_id = insert_conducteur(data)
        else:
            row_id = insert_pieton(data)

        name = f"{data.get('prenom','')} {data.get('nom','')}".strip() or data.get("numero_document", "")
        self._log(f"SAUVEGARDÉ: {name} (ID={row_id})")
        self.status_label.configure(text=f"Enregistré: {name}", text_color="#34a853")

        # Clear fields for next person
        for var in self._field_vars.values():
            var.set("")
        self.raw_input.delete("1.0", "end")
        self.focus_set()

    def _log(self, msg):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{ts}  {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _on_close(self):
        self._hid.stop()
        self.destroy()
