# admin_routes.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from re import match as re_match

from models.user import *
from models.match import *
from models.bet import *
from models.admin import *
from models.emails import *

users_bp = Blueprint("users", __name__, url_prefix="/admin/users")
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
matchs_bp = Blueprint("matchs", __name__, url_prefix="/admin/match")


def set_date(date_a_tester):
	try:
		partie_date, partie_heure = date_a_tester.split(" ")
		heure_formatee = partie_heure[:5]
	except ValueError:
		return date_a_tester

	aujourdhui = date.today().isoformat()
	hier = (date.today() - timedelta(days=1)).isoformat()
	demain = (date.today() + timedelta(days=1)).isoformat()

	if partie_date == aujourdhui:
		return f"Aujourd'hui à {heure_formatee}"
	elif partie_date == hier:
		return f"Hier à {heure_formatee}"
	elif partie_date == demain:
		return f"Demain à {heure_formatee}"
	else:
		return f"{partie_date} à {heure_formatee}"


# On définit une petite fonction utilitaire pour nettoyer proprement
def clean_input(val):
	return val.strip() if val and isinstance(val, str) else ""


# Un décorateur personnalisé pour vérifier si c'est un admin
def admin_required(f):
	def wrap(*args, **kwargs):
		if "username" not in session:
			return redirect(url_for("login"))

		user = get_user_by_username(session["username"])
		if user["classe"] != "Direction":
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


@users_bp.route("/find-user/<user_id>", methods=["POST", "GET"])
@users_bp.route("/find-user", methods=["POST", "GET"])
@admin_required
def find_user(user_id=None):
	if request.method == "GET":
		if user_id:
			users = []
			user = get_user_by_id(user_id)
			users.append(user)
			no_users = len(users) == 0
			return render_template("admin/users.html", users=users, no_users=no_users)
		else:
			return render_template("admin/users.html", no_users=True)
	# Récupération des critères
	criteres = {
		"nom": request.form.get("nom", "").strip(),
		"username": request.form.get("username_finding", "").strip(),
		"email": request.form.get("email", "").strip(),
		"age": request.form.get("age", "").strip(),
		"classe": request.form.get("classe", "").strip(),
		"notif": request.form.get("notif", "").strip(),
	}

	# Nettoyage des critères vides pour ne pas polluer la requête SQL
	filtres_actifs = {k: v for k, v in criteres.items() if v}

	users = filtrer_users_admin(filtres_actifs)

	# Déterminer si on affiche le message "Aucun utilisateur"
	no_users = len(users) == 0

	return render_template("admin/users.html", users=users, no_users=no_users)


@users_bp.route("/credit", methods=["GET", "POST"])
@admin_required
def credit_user():
	if request.method == "GET":
		return render_template("admin/users.html")

	donnees = request.form
	username = donnees.get("username_credit").strip()
	solde = donnees.get("solde_credit", "0").replace(",", ".")

	try:
		solde = int(solde)
		if solde <= 0:
			flash("Le montant doit être positif !", "error")
			return render_template("admin/users.html")
	except:
		flash("Vous devez entrer un nombre !", "error")
		return render_template("admin/users.html")

	success, message = credit(username, solde)

	flash(message)
	return redirect(url_for("admin.dashboard"))


@users_bp.route("/debit", methods=["GET", "POST"])
@admin_required
def debit_user():
	if request.method == "GET":
		return render_template("admin/users.html")

	donnees = request.form
	username = donnees.get("username_debit").strip()
	solde = donnees.get("solde_debit", "0").replace(",", ".")

	try:
		solde = int(solde)
		if solde <= 0:
			flash("Le montant doit être positif !", "error")
			return render_template("admin/users.html")
	except:
		flash("Vous devez entrer un nombre !", "error")
		return render_template("admin/users.html")

	success, message = debit(username, solde)

	flash(message)
	return redirect(url_for("admin.dashboard"))


@users_bp.route("/<action>/<username>", methods=["POST"])
@admin_required
def ban_user_route(action, username):
	user = get_user_by_username(session["username"])
	if not user or user["role"] != "super_admin":
		flash("Accès refusé", "error")
		return redirect(url_for("admin.dashboard"))

	username_adm = request.form.get("username").strip()
	password = request.form.get("password")
	message_ban_ret = request.form.get("message_ban_ret")

	if username_adm != session["username"]:
		flash("Nom d'utilisateur incorrect !", "error")
		return redirect(url_for("users.users"))

	if not check_password_hash(user["mdp"], password):
		flash("Mot de passe incorrect. Suppression annulée.", "error")
	if action == "ban":
		if ban_ret_user(username, message_ban_ret, ban=True):
			flash(f"Le joueur {username} a été suspendu !", "success")
		else:
			flash("Erreur lors de la suspension", "error")
	else:
		if ban_ret_user(username, message_ban_ret, ret=True):
			flash(f"Le joueur {username} a été rétablie !", "success")
		else:
			flash("Erreur lors du rétablissement", "error")

	return redirect(url_for("admin.dashboard"))


"""
---------------------------------------
ROUTES DES MATCHS
---------------------------------------
"""


@matchs_bp.route("/")
@admin_required
def matchs():
	return render_template("admin/matchs.html")


@matchs_bp.route("/nouveau", methods=["GET", "POST"])
@admin_required
def nouveau_match():
	if request.method == "GET":
		return render_template("admin/matchs/nouveau_match.html")
		
	equipe_a = request.form.get("equipe_a").strip()
	equipe_b = request.form.get("equipe_b").strip()
	date_match = request.form.get("date_match")
	type_match = request.form.get("type_match")

	if not all([equipe_a, equipe_b, date_match, type_match]):
		flash("L'un des champs n'a pas été rempli !", "error")
		return redirect(request.referrer)

	match_id = ajouter_match(
		equipe_a, equipe_b, date_match.replace("T", " "), type_match=type_match
	)

	if match_id:
		libelles = request.form.getlist("libelle[]")
		cotes = request.form.getlist("cote[]")
		categories = request.form.getlist("categorie[]")

		for i in range(len(libelles)):
			if libelles[i].strip() and cotes[i]:
				ajouter_option(
					libelles[i].strip(),
					float(cotes[i].replace(",", ".")),
					categories[i].strip(),
					match_id,
				)

		flash("Match ajouté avec succès !", "success")
		return redirect(url_for("admin.dashboard"))



@matchs_bp.route("/modifier", methods=["GET"])
@admin_required
def show_edit_matchs():
	mode = request.args.get("mode", "actifs")

	if mode == "archives":
		matchs_raw = get_historique_matchs()
		programmes = {}
		for m_id, m_data in matchs_raw.items():
			m_data["bilan"] = get_bilan_financier_match(m_id)
			programmes[m_id] = m_data
		titre = "Archives et Bilans Financiers"
	else:
		programmes = get_matchs_actifs()
		titre = "Matchs à traiter (Ouverts/Fermés)"

	return render_template(
		"admin/matchs/liste_matchs.html", programmes=programmes, titre=titre, mode=mode
	)


@matchs_bp.route("/modifier/<int:match_id>", methods=["GET", "POST"])
@admin_required
def edit_matchs(match_id):
	match_data = get_match_by_id(match_id)
	if not match_data:
		flash("Match introuvable !", "error")
		return redirect(url_for("matchs.show_edit_matchs"))

	if request.method == "GET":
		options = get_options_by_match_id(match_id)
		match_dict = dict(match_data)
		match_dict["date_match_local"] = (
			match_dict["date_match"][:16].replace(" ", "T") if match_dict.get("date_match") else ""
		)
		return render_template(
			"admin/matchs/modifier_match.html", match=match_dict, options=options
		)

	donnees = request.form
	equipe_a = donnees.get("equipe_a").strip()
	equipe_b = donnees.get("equipe_b").strip()
	date_match = donnees.get("date_match").replace("T", " ")
	statut = donnees.get("statut")
	type_match = donnees.get("type_match")
	update_match_info(match_id, equipe_a, equipe_b, date_match, statut, type_match)

	option_ids = request.form.getlist("option_id[]")
	categories = request.form.getlist("categorie[]")
	libelles = request.form.getlist("libelle[]")
	cotes = request.form.getlist("cote[]")

	for i in range(len(option_ids)):
		o_id = option_ids[i]
		if o_id == "0":
			ajouter_option(
				libelles[i].strip(),
				float(cotes[i]),
				categories[i].strip(),
				match_id,
			)
		else:
			update_option_info(o_id, libelles[i].strip(), float(cotes[i]), categories[i].strip())

	flash("Match mis à jour avec succès !", "success")
	return redirect(url_for("matchs.show_edit_matchs"))


@matchs_bp.route("/cloturer/<int:match_id>", methods=["GET", "POST"])
@admin_required
def cloturer_match(match_id):
	match_data = get_match_by_id(match_id)
	options = get_options_by_match_id(match_id)

	if request.method == "GET":
		return render_template(
			"admin/matchs/cloturer_match.html", match=match_data, options=options
		)

	options_gagnantes = request.form.getlist("options_gagnantes")

	for opt_id in options_gagnantes:
		valider_option_gagnante(opt_id, match_id)

	fermer_match_officiellement(match_id)
	executer_settlement_match(match_id)

	flash("Résultats enregistrés et match clôturé !", "success")
	return redirect(url_for("matchs.show_edit_matchs"))


@matchs_bp.route("/supprimer/<int:match_id>", methods=["POST"])
@admin_required
def supprimer_match_route(match_id):
	username = request.form.get("username").strip()
	password = request.form.get("password")

	if username != session["username"]:
		flash("Nom d'utilisateur incorrect !", "error")
		return redirect(url_for("matchs.show_edit_matchs"))

	user = get_user_by_username(username)
	if user and user["role"] != "parieur" and check_password_hash(user["mdp"], password):
		if supprimer_match(match_id):
			flash("Match supprimé avec succès", "success")
		else:
			flash("Erreur lors de la suppression", "error")
	else:
		flash("Mot de passe incorrect. Suppression annulée.", "error")

	return redirect(url_for("matchs.show_edit_matchs"))


"""
---------------------------------------
ROUTES DES ADMIN
---------------------------------------
"""


@admin_bp.route("/staff", methods=["POST", "GET"])
@admin_required
def staff():
	user = get_user_by_username(session["username"])
	if user["role"] != "super_admin":
		flash("Accès refusé", "error")
		return redirect(url_for("admin.dashboard"))

	if request.method == "GET":
		return render_template("admin/staff.html")

	email = request.form.get("email")
	role = request.form.get("role")
	nom = request.form.get("nom")

	if not all([email, role, nom]):
		flash("Certains champs n'ont pas été rempli !", "error")
		return redirect(request.referrer)

	token = secrets.token_urlsafe(32)
	expiration = datetime.now() + timedelta(hours=48)
	success, message = creer_invitation_admin(email, role, token, expiration)

	if success:
		lien = url_for("admin.setup_staff", token=token, _external=True)
		success_mail, # message_mail = envoyer_invitation_admin(nom, email, lien)
		if success_mail:
			flash(
				f"Invitation envoyée à {nom} ! ({email}) pour le rôle : {role}",
				"success",
			)
		else:
			flash(message_mail, "error")
	else:
		flash(message, "error")

	return redirect(url_for("admin.staff"))


@admin_bp.route("/setup_staff/<token>", methods=["GET", "POST"])
def setup_staff(token):
	invitation = get_invitation_by_token(token)
	if not invitation:
		flash("Lien d'invitation invalide.", "error")
		return redirect(url_for("home"))

	# Vérification du délai de 48h
	expire_at = datetime.strptime(invitation["expiration"], "%Y-%m-%d %H:%M:%S.%f")
	if datetime.now() > expire_at:
		flash("Ce lien a expiré.", "error")
		return "Ce lien a expiré !"

	if request.method == "GET":
		user = get_user_by_email(invitation["email"])
		if user:
			return "Cet email a déjà été utilisé. Demandez une promotion ou demandez une invitation via un autre email."
		return render_template("admin/setup_staff.html", token=token)
		

	donnees = request.form
	prenom = donnees.get("first_name", "").strip()
	nom = donnees.get("last_name", "").strip()
	username = donnees.get("username", "").strip()
	age = donnees.get("age", "")
	mdp = donnees.get("mdp", "")
	mdpConfirm = donnees.get("mdpConfirm")
	rules = donnees.get("rules")

	email = invitation["email"]
	role = invitation["role"]

	if not re_match(r"^[a-zA-Z0-9_]+$", username):
		return render_template("admin/setup_staff.html", error="Le nom d'utilisateur est invalide.")

	if len(prenom) > 20 or len(nom) > 20 or len(username) > 20:
		return render_template("admin/setup_staff.html", error="Certains champs sont trop longs !")

	if len(mdp) < 8:
		return render_template("admin/setup_staff.html", error="Le mot de passe est trop court !")

	if mdp != mdpConfirm:
		return render_template(
			"admin/setup_staff.html", error="Les mots de passe ne correspondent pas !"
		)

	if get_user_by_email(email):
		return render_template("admin/setup_staff.html", error="Cet email est déjà utilisé !")

	if get_user_by_username(username):
		return render_template(
			"admin/setup_staff.html", error="Ce nom d'utilisateur est déjà pris !"
		)

	try:
		age = int(age)
		if age < 0 or age > 100:
			raise ValueError()
	except:
		return render_template("admin/setup_staff.html", error="Veuillez entrer un âge valide.")

	if not rules:
		return render_template(
			"admin/setup_staff.html", error="Vous n'avez pas accepté les règles."
		)

	user_data = {
		"prenom": prenom,
		"nom": nom,
		"username": username,
		"email": email,
		"age": age,
		"classe": "Direction",
		"mdp": generate_password_hash(mdp),
		"role": role,
		"solde": 0,
		"created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
	}
	ajouter_parieur(user_data)
	supprimer_invitation(token)

	session["username"] = username
	flash(f"Votre compte a été créé avec succès. Bienvenue Adm {prenom}", "success")
	return redirect(url_for("home"))


@admin_bp.route("/mailbox", methods=["GET", "POST"])
@admin_required
def mailbox():
	if request.method == "GET":
		# Une seule requête SQL fait tout le travail
		messages = get_messages()

		# Si vous voulez quand même gérer l'affichage "Utilisateur supprimé"
		# directement en Python avant le template (optionnel) :
		# Comme on ne peut pas modifier un objet sqlite3.Row directement,
		# on peut convertir en dict ou gérer la logique dans le template Jinja2
		return render_template("admin/mailbox.html", messages=messages)

	donnees = request.form
	titre = donnees.get("titre").strip()
	message = donnees.get("message").strip()
	text_button = donnees.get("text_button").strip()
	lien = donnees.get("lien").strip()
	titre_popup = donnees.get("titre_popup", titre).strip()
	message_popup = donnees.get("message_popup").strip()
	key = donnees.get("key").strip()
	result = donnees.get("result")

	if key == "age":
		try:
			result = int(result)
			if result < 0 or result > 100:
				raise ValueError()
		except:
			flash("L'âge doit être un nombre entre 0 et 100.", "error")
			return redirect(request.referrer)

	emails_envoyes = 0
	notifications_envoyes = 0
	error_email = ""
	error_popup = ""

	users_list = get_users(key, result)
	for u in users_list:
		if titre:
			success, msg = envoyer_notification_generale(
				u["prenom"], u["email"], titre, message, lien, text_button
			)
			if success:
				emails_envoyes += 1
			else:
				error_email = msg

		if message_popup and titre_popup and u.get("push_subscription"):
			success_p, msg_p = envoyer_push_notification(
				u["push_subscription"], titre_popup, message_popup, lien
			)
			if success_p:
				notifications_envoyes += 1
			else:
				error_popup = msg_p

	if not error_email and not error_popup:
		flash(
			f"Emails : {emails_envoyes}, Notifications : {notifications_envoyes} envoyés.",
			"success",
		)
	else:
		flash(
			f"Erreur partielle. Emails : {emails_envoyes}, Notifications : {notifications_envoyes}",
			"error",
		)

	return redirect(url_for("admin.dashboard"))
