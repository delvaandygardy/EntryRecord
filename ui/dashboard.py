import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from datetime import datetime
import threading
import os

from config import APP_TITLE, APP_WIDTH, APP_HEIGHT, THEME
from database.db_manager import (init_db, fetch_stats, search_records, fetch_recent,
                                 get_points_entree, insert_employe, update_employe,
                                 fetch_employes, search_employes, delete_record)
from utils.helpers import export_csv, generate_daily_report_pdf, format_timestamp

ctk.set_appearance_mode(THEME)
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        init_db()
        self.title(APP_TITLE)
        self.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.minsize(1100, 650)
        self._build_layout()
        self._refresh_stats()
        self.after(5000, self._auto_refresh)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self):
        # Left sidebar
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(self.sidebar, text="ACCÈS SYSTÈME",
                     font=ctk.CTkFont(size=13, weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(self.sidebar, text="Enregistrement Auto",
                     font=ctk.CTkFont(size=10)).pack(pady=(0, 20))

        self._nav_buttons = []
        nav_items = [
            ("Tableau de Bord", self._show_dashboard),
            ("Véhicules", self._show_vehicles),
            ("Conducteurs", self._show_drivers),
            ("Piétons", self._show_pedestrians),
            ("Employés", self._show_employees),
            ("Recherche", self._show_search),
            ("Rapports", self._show_reports),
        ]
        for label, cmd in nav_items:
            btn = ctk.CTkButton(self.sidebar, text=label, command=cmd,
                                anchor="w", width=190, height=36,
                                fg_color="transparent",
                                text_color=("gray10", "gray90"),
                                hover_color=("gray70", "gray30"))
            btn.pack(pady=3, padx=15)
            self._nav_buttons.append(btn)

        ctk.CTkLabel(self.sidebar, text="").pack(expand=True)
        self.clock_label = ctk.CTkLabel(self.sidebar, text="", font=ctk.CTkFont(size=11))
        self.clock_label.pack(pady=(0, 20))
        self._tick_clock()

        # Main area
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self._pages = {}
        self._build_dashboard_page()
        self._build_vehicles_page()
        self._build_drivers_page()
        self._build_pedestrians_page()
        self._build_employees_page()
        self._build_search_page()
        self._build_reports_page()
        self._show_dashboard()

    # ------------------------------------------------------------------
    # Page switching
    # ------------------------------------------------------------------

    def _show_page(self, name):
        for page in self._pages.values():
            page.pack_forget()
        self._pages[name].pack(fill="both", expand=True)

    def _show_dashboard(self):   self._show_page("dashboard")
    def _show_vehicles(self):
        self._show_page("vehicles"); self._load_table("vehicles")
    def _show_drivers(self):
        self._show_page("drivers"); self._load_table("drivers")
    def _show_pedestrians(self):
        self._show_page("pedestrians"); self._load_table("pedestrians")
    def _show_employees(self):
        self._show_page("employees"); self._load_employees()
    def _show_search(self):      self._show_page("search")
    def _show_reports(self):
        self._show_page("reports"); self._refresh_stats()

    # ------------------------------------------------------------------
    # Dashboard page
    # ------------------------------------------------------------------

    def _build_dashboard_page(self):
        page = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self._pages["dashboard"] = page

        ctk.CTkLabel(page, text="Tableau de Bord",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w", pady=(10, 20))

        cards_frame = ctk.CTkFrame(page, fg_color="transparent")
        cards_frame.pack(fill="x")

        self._stat_labels = {}
        cards = [
            ("vehicules_today", "Véhicules\naujourd'hui", "#1a73e8"),
            ("conducteurs_today", "Conducteurs\naujourd'hui", "#34a853"),
            ("pietons_today", "Piétons\naujourd'hui", "#fbbc04"),
            ("vehicules_total", "Total\nVéhicules", "#ea4335"),
        ]
        for col, (key, label, color) in enumerate(cards):
            frame = ctk.CTkFrame(cards_frame, width=180, height=110,
                                 fg_color=color, corner_radius=12)
            frame.grid(row=0, column=col, padx=10, pady=5, sticky="nsew")
            frame.pack_propagate(False)
            num = ctk.CTkLabel(frame, text="0",
                               font=ctk.CTkFont(size=36, weight="bold"),
                               text_color="white")
            num.pack(pady=(15, 2))
            ctk.CTkLabel(frame, text=label, text_color="white",
                         font=ctk.CTkFont(size=11)).pack()
            self._stat_labels[key] = num
            cards_frame.columnconfigure(col, weight=1)

        # Quick-action buttons
        ctk.CTkLabel(page, text="Actions Rapides",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(25, 10))
        btn_frame = ctk.CTkFrame(page, fg_color="transparent")
        btn_frame.pack(fill="x")

        actions = [
            ("Ouvrir Caméra Plaque", "#1a73e8", self._open_camera_window),
            ("Scanner Conducteur", "#34a853", self._open_driver_scanner),
            ("Scanner Piéton", "#fbbc04", self._open_pedestrian_scanner),
        ]
        for col, (text, color, cmd) in enumerate(actions):
            ctk.CTkButton(btn_frame, text=text, fg_color=color,
                          width=210, height=50, command=cmd,
                          font=ctk.CTkFont(size=13)).grid(
                row=0, column=col, padx=10, pady=5)
            btn_frame.columnconfigure(col, weight=1)

        # Recent activity feed
        ctk.CTkLabel(page, text="Activité Récente",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(25, 5))
        self.activity_box = ctk.CTkTextbox(page, height=220, state="disabled",
                                           font=ctk.CTkFont(size=12, family="Courier"))
        self.activity_box.pack(fill="x")
        self._refresh_activity()

    def _refresh_stats(self):
        from database.db_manager import fetch_stats
        stats = fetch_stats()
        for key, lbl in self._stat_labels.items():
            lbl.configure(text=str(stats.get(key, 0)))

    def _refresh_activity(self):
        vehs = fetch_recent("vehicules", 5)
        drivers = fetch_recent("conducteurs", 5)
        pietons = fetch_recent("pietons", 5)
        lines = []
        for v in vehs:
            lines.append(f"[VÉHICULE]   {format_timestamp(v['timestamp'])}  —  {v['plaque']}")
        for d in drivers:
            name = f"{d.get('prenom','')} {d.get('nom','')}".strip()
            lines.append(f"[CONDUCTEUR] {format_timestamp(d['timestamp'])}  —  {name or d.get('numero_document','')}")
        for p in pietons:
            name = f"{p.get('prenom','')} {p.get('nom','')}".strip()
            lines.append(f"[PIÉTON]     {format_timestamp(p['timestamp'])}  —  {name or p.get('numero_document','')}")
        lines.sort(reverse=True)
        self.activity_box.configure(state="normal")
        self.activity_box.delete("1.0", "end")
        self.activity_box.insert("end", "\n".join(lines[:15]))
        self.activity_box.configure(state="disabled")

    def _auto_refresh(self):
        self._refresh_stats()
        self._refresh_activity()
        self.after(5000, self._auto_refresh)

    # ------------------------------------------------------------------
    # Reusable table builder
    # ------------------------------------------------------------------

    def _build_table_page(self, name, columns, col_labels):
        page = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self._pages[name] = page

        titles = {"vehicles": "Véhicules", "drivers": "Conducteurs", "pedestrians": "Piétons"}
        ctk.CTkLabel(page, text=titles.get(name, name),
                     font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(10, 10))

        # Treeview
        tree_frame = ctk.CTkFrame(page)
        tree_frame.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Custom.Treeview", rowheight=28, font=("Helvetica", 12))
        style.configure("Custom.Treeview.Heading", font=("Helvetica", 12, "bold"))

        tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                            style="Custom.Treeview", selectmode="browse")
        for col, lbl in zip(columns, col_labels):
            tree.heading(col, text=lbl)
            tree.column(col, width=130, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)

        # Store reference
        setattr(self, f"_{name}_tree", tree)
        setattr(self, f"_{name}_cols", columns)

        # Bottom bar
        bar = ctk.CTkFrame(page, fg_color="transparent")
        bar.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(bar, text="Exporter CSV", width=130,
                      command=lambda n=name: self._export_table(n)).pack(side="left", padx=5)
        ctk.CTkButton(bar, text="Actualiser", width=110,
                      command=lambda n=name: self._load_table(n)).pack(side="left", padx=5)

        return page

    def _load_table(self, name):
        table_map = {"vehicles": "vehicules", "drivers": "conducteurs", "pedestrians": "pietons"}
        db_table = table_map[name]
        rows = fetch_recent(db_table, 500)
        tree = getattr(self, f"_{name}_tree")
        cols = getattr(self, f"_{name}_cols")
        tree.delete(*tree.get_children())
        for row in rows:
            vals = [str(row.get(c, "")) for c in cols]
            tree.insert("", "end", values=vals)

    def _export_table(self, name):
        table_map = {"vehicles": "vehicules", "drivers": "conducteurs", "pedestrians": "pietons"}
        db_table = table_map[name]
        rows = fetch_recent(db_table, 5000)
        if not rows:
            messagebox.showinfo("Export", "Aucune donnée à exporter.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if path:
            export_csv(rows, path, list(rows[0].keys()))
            messagebox.showinfo("Export", f"Fichier sauvegardé:\n{path}")

    def _build_vehicles_page(self):
        cols = ["id", "plaque", "confidence", "timestamp", "point_entree", "notes"]
        labels = ["ID", "Plaque", "Confiance", "Date/Heure", "Point d'Entrée", "Notes"]
        self._build_table_page("vehicles", cols, labels)

    def _build_drivers_page(self):
        cols = ["id", "nom", "prenom", "numero_document", "type_document",
                "date_naissance", "timestamp", "point_entree"]
        labels = ["ID", "Nom", "Prénom", "N° Document", "Type", "Naissance", "Date/Heure", "Entrée"]
        self._build_table_page("drivers", cols, labels)

    def _build_pedestrians_page(self):
        cols = ["id", "nom", "prenom", "numero_document", "type_document",
                "date_naissance", "nationalite", "timestamp", "point_entree"]
        labels = ["ID", "Nom", "Prénom", "N° Document", "Type", "Naissance",
                  "Nationalité", "Date/Heure", "Entrée"]
        self._build_table_page("pedestrians", cols, labels)

    # ------------------------------------------------------------------
    # Employees page
    # ------------------------------------------------------------------

    def _build_employees_page(self):
        page = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self._pages["employees"] = page

        ctk.CTkLabel(page, text="Employés",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(10, 5))

        # Toolbar
        bar = ctk.CTkFrame(page, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))

        self._emp_search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(bar, textvariable=self._emp_search_var,
                                     placeholder_text="Rechercher…", width=260, height=34)
        search_entry.pack(side="left", padx=(0, 8))
        search_entry.bind("<Return>", lambda e: self._search_employees())
        ctk.CTkButton(bar, text="Rechercher", width=110, height=34,
                      command=self._search_employees).pack(side="left", padx=(0, 15))

        ctk.CTkButton(bar, text="+ Ajouter Employé", width=150, height=34,
                      fg_color="#34a853",
                      command=self._open_employee_form).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bar, text="Modifier", width=100, height=34,
                      command=self._edit_selected_employee).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bar, text="Supprimer", width=100, height=34,
                      fg_color="#ea4335",
                      command=self._delete_selected_employee).pack(side="left", padx=(0, 8))
        ctk.CTkButton(bar, text="Exporter CSV", width=120, height=34,
                      command=self._export_employees_csv).pack(side="left")

        # Filtre statut
        self._emp_statut_var = tk.StringVar(value="Tous")
        ctk.CTkOptionMenu(bar, variable=self._emp_statut_var,
                           values=["Tous", "Actif", "Inactif"],
                           width=110, height=34,
                           command=lambda _: self._load_employees()).pack(side="right")
        ctk.CTkLabel(bar, text="Statut:").pack(side="right", padx=(0, 5))

        # Treeview
        tree_frame = ctk.CTkFrame(page)
        tree_frame.pack(fill="both", expand=True)

        cols = ["id", "matricule", "nom", "prenom", "poste", "departement",
                "telephone", "email", "date_embauche", "statut"]
        labels = ["ID", "Matricule", "Nom", "Prénom", "Poste", "Département",
                  "Téléphone", "Email", "Date Embauche", "Statut"]

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Emp.Treeview", rowheight=28, font=("Helvetica", 12))
        style.configure("Emp.Treeview.Heading", font=("Helvetica", 12, "bold"))
        style.map("Emp.Treeview", background=[("selected", "#1a73e8")])

        self._emp_tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                       style="Emp.Treeview", selectmode="browse")
        widths = [40, 90, 120, 120, 130, 130, 110, 160, 110, 70]
        for col, lbl, w in zip(cols, labels, widths):
            self._emp_tree.heading(col, text=lbl)
            self._emp_tree.column(col, width=w, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._emp_tree.yview)
        self._emp_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._emp_tree.pack(fill="both", expand=True)

        # Color inactive rows
        self._emp_tree.tag_configure("inactif", foreground="gray")

    def _load_employees(self):
        statut = self._emp_statut_var.get()
        rows = fetch_employes(statut=None if statut == "Tous" else statut)
        self._emp_tree.delete(*self._emp_tree.get_children())
        for row in rows:
            vals = [str(row.get(c, "") or "") for c in
                    ["id", "matricule", "nom", "prenom", "poste", "departement",
                     "telephone", "email", "date_embauche", "statut"]]
            tag = "inactif" if row.get("statut") == "Inactif" else ""
            self._emp_tree.insert("", "end", values=vals, tags=(tag,))

    def _search_employees(self):
        q = self._emp_search_var.get().strip()
        rows = search_employes(q) if q else fetch_employes()
        self._emp_tree.delete(*self._emp_tree.get_children())
        for row in rows:
            vals = [str(row.get(c, "") or "") for c in
                    ["id", "matricule", "nom", "prenom", "poste", "departement",
                     "telephone", "email", "date_embauche", "statut"]]
            tag = "inactif" if row.get("statut") == "Inactif" else ""
            self._emp_tree.insert("", "end", values=vals, tags=(tag,))

    def _get_selected_employee_id(self):
        sel = self._emp_tree.selection()
        if not sel:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un employé.")
            return None
        return int(self._emp_tree.item(sel[0])["values"][0])

    def _open_employee_form(self, prefill=None):
        EmployeeForm(self, on_save=self._load_employees, prefill=prefill)

    def _edit_selected_employee(self):
        sel = self._emp_tree.selection()
        if not sel:
            messagebox.showwarning("Sélection", "Veuillez sélectionner un employé.")
            return
        vals = self._emp_tree.item(sel[0])["values"]
        keys = ["id", "matricule", "nom", "prenom", "poste", "departement",
                "telephone", "email", "date_embauche", "statut"]
        prefill = dict(zip(keys, vals))
        self._open_employee_form(prefill=prefill)

    def _delete_selected_employee(self):
        emp_id = self._get_selected_employee_id()
        if emp_id is None:
            return
        if messagebox.askyesno("Supprimer", f"Supprimer l'employé ID {emp_id} ?"):
            delete_record("employes", emp_id)
            self._load_employees()

    def _export_employees_csv(self):
        rows = fetch_employes()
        if not rows:
            messagebox.showinfo("Export", "Aucune donnée à exporter.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV", "*.csv")],
                                             initialfile="employes.csv")
        if path:
            export_csv(rows, path, list(rows[0].keys()))
            messagebox.showinfo("Export", f"Fichier sauvegardé:\n{path}")

    # ------------------------------------------------------------------
    # Search page
    # ------------------------------------------------------------------

    def _build_search_page(self):
        page = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self._pages["search"] = page

        ctk.CTkLabel(page, text="Recherche",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(10, 10))

        top = ctk.CTkFrame(page, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))
        self.search_entry = ctk.CTkEntry(top, placeholder_text="Plaque, nom, numéro de document…",
                                         width=400, height=38, font=ctk.CTkFont(size=13))
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self._do_search())
        ctk.CTkButton(top, text="Rechercher", width=120, height=38,
                      command=self._do_search).pack(side="left")

        self.search_result_box = ctk.CTkTextbox(page, state="disabled",
                                                 font=ctk.CTkFont(size=12, family="Courier"))
        self.search_result_box.pack(fill="both", expand=True)

    def _do_search(self):
        q = self.search_entry.get().strip()
        if not q:
            return
        results = search_records(q)
        lines = []
        for cat, rows in results.items():
            if rows:
                lines.append(f"=== {cat.upper()} ({len(rows)} résultat(s)) ===")
                for r in rows[:50]:
                    lines.append("  " + " | ".join(f"{k}: {v}" for k, v in r.items()
                                                     if v and k not in ("id", "raw_scan", "image_path")))
                lines.append("")
        text = "\n".join(lines) if lines else "Aucun résultat trouvé."
        self.search_result_box.configure(state="normal")
        self.search_result_box.delete("1.0", "end")
        self.search_result_box.insert("end", text)
        self.search_result_box.configure(state="disabled")

    # ------------------------------------------------------------------
    # Reports page
    # ------------------------------------------------------------------

    def _build_reports_page(self):
        page = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self._pages["reports"] = page

        ctk.CTkLabel(page, text="Rapports",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(10, 20))

        self.report_stats_label = ctk.CTkLabel(page, text="", justify="left",
                                                font=ctk.CTkFont(size=13))
        self.report_stats_label.pack(anchor="w", padx=20)

        ctk.CTkButton(page, text="Exporter Rapport PDF du Jour",
                      width=260, height=44, font=ctk.CTkFont(size=13),
                      command=self._export_pdf).pack(pady=20)

        self._refresh_report_stats()

    def _refresh_report_stats(self):
        from database.db_manager import fetch_stats
        s = fetch_stats()
        today = datetime.now().strftime("%d/%m/%Y")
        text = (f"Date: {today}\n\n"
                f"Véhicules aujourd'hui:   {s.get('vehicules_today', 0)}\n"
                f"Conducteurs aujourd'hui: {s.get('conducteurs_today', 0)}\n"
                f"Piétons aujourd'hui:     {s.get('pietons_today', 0)}\n\n"
                f"Total véhicules:    {s.get('vehicules_total', 0)}\n"
                f"Total conducteurs:  {s.get('conducteurs_total', 0)}\n"
                f"Total piétons:      {s.get('pietons_total', 0)}\n")
        if hasattr(self, "report_stats_label"):
            self.report_stats_label.configure(text=text)

    def _export_pdf(self):
        from database.db_manager import fetch_stats
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"rapport_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
        if path:
            ok = generate_daily_report_pdf(fetch_stats(), path)
            if ok:
                messagebox.showinfo("Rapport", f"Rapport sauvegardé:\n{path}")
            else:
                messagebox.showerror("Erreur", "reportlab non installé. Essayez:\npip install reportlab")

    # ------------------------------------------------------------------
    # Camera window (ALPR)
    # ------------------------------------------------------------------

    def _open_camera_window(self):
        from ui.camera_window import CameraWindow
        CameraWindow(self)

    def _open_driver_scanner(self):
        from ui.scanner_window import ScannerWindow
        ScannerWindow(self, mode="conducteur")

    def _open_pedestrian_scanner(self):
        from ui.scanner_window import ScannerWindow
        ScannerWindow(self, mode="pieton")

    # ------------------------------------------------------------------
    # Clock
    # ------------------------------------------------------------------

    def _tick_clock(self):
        now = datetime.now().strftime("%H:%M:%S\n%d/%m/%Y")
        self.clock_label.configure(text=now)
        self.after(1000, self._tick_clock)


def run():
    app = App()
    app.mainloop()


class EmployeeForm(ctk.CTkToplevel):
    """Formulaire d'ajout et de modification d'un employé."""

    FIELDS = [
        ("Matricule *",    "matricule"),
        ("Nom *",          "nom"),
        ("Prénom *",       "prenom"),
        ("Poste",          "poste"),
        ("Département",    "departement"),
        ("Téléphone",      "telephone"),
        ("Email",          "email"),
        ("Date Embauche",  "date_embauche"),
    ]

    def __init__(self, parent, on_save, prefill=None):
        super().__init__(parent)
        self._on_save = on_save
        self._edit_id = int(prefill["id"]) if prefill and prefill.get("id") else None
        title = "Modifier Employé" if self._edit_id else "Ajouter Employé"
        self.title(title)
        self.geometry("440x560")
        self.resizable(False, False)
        self._vars = {}
        self._build(prefill or {})

    def _build(self, prefill):
        ctk.CTkLabel(self, text=self.title(),
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10))

        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=20)

        for i, (label, key) in enumerate(self.FIELDS):
            ctk.CTkLabel(form, text=label, anchor="w",
                         font=ctk.CTkFont(size=12)).grid(row=i, column=0, sticky="w",
                                                          padx=(10, 5), pady=5)
            var = tk.StringVar(value=str(prefill.get(key, "") or ""))
            ctk.CTkEntry(form, textvariable=var, width=240,
                         height=32).grid(row=i, column=1, sticky="w", pady=5)
            self._vars[key] = var

        # Statut
        row = len(self.FIELDS)
        ctk.CTkLabel(form, text="Statut", anchor="w",
                     font=ctk.CTkFont(size=12)).grid(row=row, column=0, sticky="w",
                                                      padx=(10, 5), pady=5)
        self._statut_var = tk.StringVar(value=prefill.get("statut", "Actif"))
        ctk.CTkOptionMenu(form, variable=self._statut_var,
                           values=["Actif", "Inactif"],
                           width=240).grid(row=row, column=1, sticky="w", pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Enregistrer", width=150, height=38,
                      fg_color="#34a853",
                      command=self._save).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Annuler", width=100, height=38,
                      fg_color="transparent", border_width=1,
                      command=self.destroy).pack(side="left", padx=10)

    def _save(self):
        data = {k: v.get().strip() for k, v in self._vars.items()}
        data["statut"] = self._statut_var.get()

        if not data.get("matricule") or not data.get("nom") or not data.get("prenom"):
            messagebox.showwarning("Champs requis",
                                   "Matricule, Nom et Prénom sont obligatoires.")
            return
        try:
            if self._edit_id:
                update_employe(self._edit_id, data)
            else:
                insert_employe(data)
            self._on_save()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))
