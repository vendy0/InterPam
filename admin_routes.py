# admin_routes.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from data import (
    get_user_by_username,
    get_user_by_email,
    get_user_by_name,
    get_user_by_age,
    get_user_by_grade,
    ajouter_parieur,
    filtrer_users_admin,
    ajouter_match,
    ajouter_option,
    credit,
)

users_bp = Blueprint("users", __name__, url_prefix="/admin/users")
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
matchs_bp = Blueprint("matchs", __name__, url_prefix="/admin/match")


# Un décorateur personnalisé pour vérifier si c'est un admin
def admin_required(f):
    def wrap(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))

        user = get_user_by_username(session["username"])
        if user["role"] not in ["super_admin", "admin", "statisticien"]:
            flash("Accès interdit", "error")
            return redirect(url_for("home"))

        return f(*args, **kwargs)

    wrap.__name__ = f.__name__
    return wrap


@admin_bp.route("/")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html")


"""
---------------------------------------
ROUTES DES USERS
---------------------------------------
"""


@users_bp.route("/")
@admin_required
def users():
    return render_template("admin/users.html")


@users_bp.route("/find-user", methods=["POST", "GET"])
@admin_required
def find_user():
    if request.method == "GET":
        return render_template("admin/users.html")

    criteres = {
        "nom": request.form.get("nom"),
        "username": request.form.get("username_finding"),
        "email": request.form.get("email"),
        "age": request.form.get("age"),
        "classe": request.form.get("classe"),
    }

    # On appelle la fonction de filtrage strict (AND)
    resultats = filtrer_users_admin(criteres)

    if len(resultats) > 0:
        return render_template("admin/users.html", users=resultats)
    else:
        return render_template("admin/users.html", no_users="no users")


@users_bp.route("/credit", methods=["GET", "POST"])
@admin_required
def credit_user():
    if request.method == "GET":
        return render_template("admin/users.html")

    donnees = request.form
    username = donnees.get("username_credit")
    solde = donnees.get("solde", "0").replace(",", ".")

    try:
        solde = int(solde)
        if solde <= 0:
            flash("Le montant doit être positif !")
            return render_template("admin/users.html")
    except:
        flash("Vous devez entrer un nombre !")
        return render_template("admin/users.html")

    succes, message = credit(username, solde)

    flash(message)
    return render_template("admin/users.html")


"""
---------------------------------------
ROUTES DES MATCHS
---------------------------------------
"""


@matchs_bp.route("/")
@admin_required  #
def matchs():
    return render_template("admin/matchs.html")


@matchs_bp.route("/nouveau", methods=["GET", "POST"])
@admin_required  #
def nouveau_match():
    if request.method == "POST":
        equipe_a = request.form.get("equipe_a")
        equipe_b = request.form.get("equipe_b")
        date_match = request.form.get("date_match")

        # 1. Création du match
        match_id = ajouter_match(equipe_a, equipe_b, date_match)  #

        if match_id:
            # 2. Récupération des listes dynamiques
            libelles = request.form.getlist("libelle[]")
            cotes = request.form.getlist("cote[]")
            categories = request.form.getlist("categorie[]")

            # 3. Insertion de toutes les options
            for i in range(len(libelles)):
                if libelles[i] and cotes[i]:
                    ajouter_option(
                        libelles[i],
                        float(cotes[i].replace(",", ".")),
                        categories[i],
                        match_id,
                    )  #

            flash("Match ajouté avec succès !", "success")
            return redirect(url_for("admin.dashboard"))  #

    return render_template("admin/matchs/nouveau_match.html")
