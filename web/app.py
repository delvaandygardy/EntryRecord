import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from database.db_manager import (
    init_db, fetch_stats, fetch_recent, search_records,
    insert_employe, update_employe, fetch_employes, search_employes,
    delete_record, get_points_entree,
    insert_vehicule, insert_conducteur, insert_pieton,
)
from utils.helpers import export_csv
import tempfile

app = Flask(__name__)
init_db()


# ── Helpers ────────────────────────────────────────────────────────────────

def _page_data():
    return {"stats": fetch_stats(), "points": get_points_entree()}


# ── Dashboard ──────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    stats = fetch_stats()
    recent = {
        "vehicules":   fetch_recent("vehicules",   10),
        "conducteurs": fetch_recent("conducteurs", 5),
        "pietons":     fetch_recent("pietons",      5),
        "employes":    fetch_recent("employes",     5),
    }
    return render_template("dashboard.html", stats=stats, recent=recent)


# ── Stats JSON (auto-refresh) ──────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    return jsonify(fetch_stats())


# ── Véhicules ──────────────────────────────────────────────────────────────

@app.route("/vehicules")
def vehicules():
    rows = fetch_recent("vehicules", 500)
    return render_template("table_view.html", title="Véhicules",
                           rows=rows,
                           cols=["id","plaque","confidence","point_entree","timestamp","notes"],
                           labels=["ID","Plaque","Confiance","Point d'Entrée","Date/Heure","Notes"],
                           add_url=url_for("add_vehicule"),
                           export_url=url_for("export_csv_route", table="vehicules"))


@app.route("/vehicules/ajouter", methods=["GET","POST"])
def add_vehicule():
    if request.method == "POST":
        insert_vehicule(
            request.form["plaque"],
            float(request.form.get("confidence") or 1.0),
            None,
            request.form.get("point_entree", "Principal"),
            request.form.get("notes")
        )
        return redirect(url_for("vehicules"))
    return render_template("form_vehicule.html", points=get_points_entree())


# ── Conducteurs ────────────────────────────────────────────────────────────

@app.route("/conducteurs")
def conducteurs():
    rows = fetch_recent("conducteurs", 500)
    return render_template("table_view.html", title="Conducteurs",
                           rows=rows,
                           cols=["id","nom","prenom","numero_document","type_document",
                                 "date_naissance","point_entree","timestamp"],
                           labels=["ID","Nom","Prénom","N° Document","Type",
                                   "Naissance","Entrée","Date/Heure"],
                           add_url=url_for("add_conducteur"),
                           export_url=url_for("export_csv_route", table="conducteurs"))


@app.route("/conducteurs/ajouter", methods=["GET","POST"])
def add_conducteur():
    if request.method == "POST":
        insert_conducteur(request.form.to_dict())
        return redirect(url_for("conducteurs"))
    return render_template("form_personne.html", title="Ajouter Conducteur",
                           type_doc_default="PERMIS", points=get_points_entree())


# ── Piétons ────────────────────────────────────────────────────────────────

@app.route("/pietons")
def pietons():
    rows = fetch_recent("pietons", 500)
    return render_template("table_view.html", title="Piétons",
                           rows=rows,
                           cols=["id","nom","prenom","numero_document","type_document",
                                 "date_naissance","nationalite","point_entree","timestamp"],
                           labels=["ID","Nom","Prénom","N° Document","Type",
                                   "Naissance","Nationalité","Entrée","Date/Heure"],
                           add_url=url_for("add_pieton"),
                           export_url=url_for("export_csv_route", table="pietons"))


@app.route("/pietons/ajouter", methods=["GET","POST"])
def add_pieton():
    if request.method == "POST":
        insert_pieton(request.form.to_dict())
        return redirect(url_for("pietons"))
    return render_template("form_personne.html", title="Ajouter Piéton",
                           type_doc_default="CNI", points=get_points_entree())


# ── Employés ───────────────────────────────────────────────────────────────

@app.route("/employes")
def employes():
    statut = request.args.get("statut")
    q      = request.args.get("q", "")
    if q:
        rows = search_employes(q)
    else:
        rows = fetch_employes(statut=statut)
    return render_template("employes.html", rows=rows, statut=statut or "Tous", q=q)


@app.route("/employes/ajouter", methods=["GET","POST"])
def add_employe():
    if request.method == "POST":
        insert_employe(request.form.to_dict())
        return redirect(url_for("employes"))
    return render_template("form_employe.html", title="Ajouter Employé", emp={})


@app.route("/employes/<int:emp_id>/modifier", methods=["GET","POST"])
def edit_employe(emp_id):
    if request.method == "POST":
        update_employe(emp_id, request.form.to_dict())
        return redirect(url_for("employes"))
    rows = fetch_employes()
    emp = next((r for r in rows if r["id"] == emp_id), {})
    return render_template("form_employe.html", title="Modifier Employé", emp=emp)


@app.route("/employes/<int:emp_id>/supprimer", methods=["POST"])
def delete_employe(emp_id):
    delete_record("employes", emp_id)
    return redirect(url_for("employes"))


# ── Recherche ──────────────────────────────────────────────────────────────

@app.route("/recherche")
def recherche():
    q = request.args.get("q", "").strip()
    results = search_records(q) if q else {}
    emp_results = search_employes(q) if q else []
    return render_template("recherche.html", q=q, results=results, emp_results=emp_results)


# ── Suppression générique ──────────────────────────────────────────────────

@app.route("/supprimer/<table>/<int:record_id>", methods=["POST"])
def supprimer(table, record_id):
    allowed = {"vehicules", "conducteurs", "pietons"}
    if table in allowed:
        delete_record(table, record_id)
    return redirect(request.referrer or url_for("dashboard"))


# ── Export CSV ─────────────────────────────────────────────────────────────

@app.route("/export/<table>")
def export_csv_route(table):
    allowed = {"vehicules": 500, "conducteurs": 500, "pietons": 500, "employes": 500}
    if table not in allowed:
        return "Table non autorisée", 403
    if table == "employes":
        rows = fetch_employes()
    else:
        rows = fetch_recent(table, allowed[table])
    if not rows:
        return "Aucune donnée", 204
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="w", encoding="utf-8")
    tmp.close()
    export_csv(rows, tmp.name, list(rows[0].keys()))
    return send_file(tmp.name, as_attachment=True,
                     download_name=f"{table}.csv", mimetype="text/csv")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
