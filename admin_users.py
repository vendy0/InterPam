from flask import Blueprint, render_template, request, redirect, url_for, flash
from data import ajouter_parieur, recuperer_utilisateur_par_email, recuperer_utilisateur_par_username, recuperer_utilisateur_par_nom # On peut réutiliser la même fonction
from admin_routes import admin_required # On importe ton garde du corps

users_bp = Blueprint('admin_users', __name__, url_prefix='/admin/users')

@users_bp.route("/")
@admin_required
def users():
    # Ici tu appelleras une fonction pour lister les admins ou parieurs
    return render_template("admin/users.html")

@users_bp.route("/find-user", methods=['POST', 'GET'])
@admin_required
def find_user():
	if request.method == "GET":
		return render_template("admin/users/find_user.html")


# @users_bp.route("/add", methods=["GET", "POST"])
# @admin_required
# def ajouter_membre_staff():
#     if request.method == "POST":
#         # Logique pour récupérer le formulaire et enregistrer un nouvel admin
#         # (N'oublie pas de forcer le rôle 'admin' ou 'statisticien' ici)
#         pass
#     return render_template("admin/add_user.html")
