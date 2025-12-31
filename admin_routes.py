# admin_routes.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from models.emails import welcome_email
from re import match

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


@users_bp.route("/find-user", methods=["POST", "GET"])
@admin_required
def find_user():
	if request.method == "GET":
		return render_template("admin/users.html")
	criteres = {
		"nom": request.form.get("nom").strip(),
		"username": request.form.get("username_finding").strip(),
		"email": request.form.get("email").strip(),
		"age": request.form.get("age"),
		"classe": request.form.get("classe"),
	}

	# On appelle la fonction de filtrage strict (AND)
	resultats = filtrer_users_admin(criteres)
	if len(resultats) > 0:
		return render_template(
			"admin/users.html",
			users=resultats,
			current_user=get_user_by_username(session["username"]),
		)
	else:
		return render_template("admin/users.html", no_users="no users")


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
			flash("Le montant doit être positif !")
			return render_template("admin/users.html")
	except:
		flash("Vous devez entrer un nombre !")
		return render_template("admin/users.html")

	succes, message = credit(username, solde)

	flash(message)
	return render_template("admin/users.html")


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
			flash("Le montant doit être positif !")
			return render_template("admin/users.html")
	except:
		flash("Vous devez entrer un nombre !")
		return render_template("admin/users.html")

	succes, message = debit(username, solde)

	flash(message)
	return render_template("admin/users.html")


@users_bp.route("/<action>/<username>", methods=["POST"])
@admin_required
def ban_user_route(action, username):
	user = get_user_by_username(session["username"])
	if not user or user["role"] != "super_admin":
		flash("Accès refusé", "error")
		return redirect(url_for("admin.dashboard"))

	username_adm = request.form.get("username").strip()
	password = request.form.get("password")

	if username_adm != session["username"]:
		flash("Nom d'utilisateur incorrect !")
		return redirect(url_for("users.users"))

	# Remplacez par votre logique de vérification (ex: check_password_hash)
	# Ici, je suppose une comparaison simple ou via une fonction dédiée
	if check_password_hash(user["mdp"], password):
		if action == "ban":
			if ban_ret_user(username, ban="ban"):
				flash(f"Le joueur {username} a été suspendu !", "success")
			else:
				flash("Erreur lors de la suspension", "error")
		else:
			if ban_ret_user(username, ret="ret"):
				flash(f"Le joueur {username} a été rétablie !", "success")
			else:
				flash("Erreur lors du rétablissement", "error")
	else:
		flash("Mot de passe incorrect. Suppression annulée.", "error")

	return redirect(url_for("users.users"))


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
		equipe_a = request.form.get("equipe_a").strip()
		equipe_b = request.form.get("equipe_b").strip()
		date_match = request.form.get("date_match")

		# 1. Création du match
		match_id = ajouter_match(equipe_a, equipe_b, date_match.replace("T", " "))  #

		if match_id:
			# 2. Récupération des listes dynamiques
			libelles = request.form.getlist("libelle[]")
			cotes = request.form.getlist("cote[]")
			categories = request.form.getlist("categorie[]")

			# 3. Insertion de toutes les options
			for i in range(len(libelles)):
				if libelles[i].strip() and cotes[i]:
					ajouter_option(
						libelles[i].strip(),
						float(cotes[i].replace(",", ".")),
						categories[i].strip(),
						match_id,
					)  #

			flash("Match ajouté avec succès !", "success")
			return redirect(url_for("admin.dashboard"))  #

	return render_template("admin/matchs/nouveau_match.html")


@matchs_bp.route("/modifier", methods=["GET"])
@admin_required
def show_edit_matchs():
	# On récupère le paramètre 'mode' dans l'URL (ex: /modifier?mode=archives)
	mode = request.args.get("mode", "actifs")

	if mode == "archives":
		matchs_raw = get_historique_matchs()
		programmes = {}
		# On injecte le bilan financier pour chaque match archivé
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
@admin_required  #
def edit_matchs(match_id):
	programmes = get_programmes()
	match_data = get_match_by_id(match_id)
	# convertir row en dict si nécessaire
	match_dict = dict(match_data)
	# on prend les 16 premiers caractères "YYYY-MM-DD HH:MM"
	# et on remplace l'espace par 'T' pour datetime-local "YYYY-MM-DDTHH:MM"
	if match_dict.get("date_match"):
		match_dict["date_match_local"] = match_dict["date_match"][:16].replace(" ", "T")
	else:
		match_dict["date_match_local"] = ""

	if not match_data:
		flash("Match introuvable !", "error")
		return redirect(url_for("match.show_edit_matchs"))

	""" --- MISE À JOUR DU MATCH --- """
	if request.method == "POST":
		donnees = request.form
		equipe_a = donnees.get("equipe_a").strip()
		equipe_b = donnees.get("equipe_b").strip()
		date_match = donnees.get("date_match").replace("T", " ")
		statut = donnees.get("statut")
		type_match = donnees.get("type_match")
		update_match_info(match_id, equipe_a, equipe_b, date_match, statut, type_match)

		""" --- MISE À JOUR / AJOUT DES OPTIONS --- """
		# --- MISE À JOUR / AJOUT DES OPTIONS ---
		option_ids = request.form.getlist("option_id[]")
		categories = request.form.getlist("categorie[]")
		libelles = request.form.getlist("libelle[]")
		cotes = request.form.getlist("cote[]")

		for i in range(len(option_ids)):
			o_id = option_ids[i]
			# Si l'id est "0", c'est une nouvelle ligne ajoutée en JS
			if o_id == "0":
				ajouter_option(
					libelles[i].strip(),
					float(cotes[i]),
					categories[i].strip(),
					match_id,
				)  #
			else:
				update_option_info(
					o_id, libelles[i].strip(), float(cotes[i]), categories[i].strip()
				)

		flash("Match mis à jour avec succès !")
		return redirect(url_for("matchs.show_edit_matchs"))

	# 2. Affichage du formulaire (GET)
	options = get_options_by_match_id(match_id)
	match_dict = dict(match_data)
	match_dict["date_match_local"] = (
		match_dict["date_match"][:16].replace(" ", "T") if match_dict.get("date_match") else ""
	)
	return render_template("admin/matchs/modifier_match.html", match=match_dict, options=options)


@matchs_bp.route("/cloturer/<int:match_id>", methods=["GET", "POST"])
@admin_required
def cloturer_match(match_id):
	match_data = get_match_by_id(match_id)
	options = get_options_by_match_id(match_id)

	if request.method == "POST":
		# On récupère les IDs des options cochées comme gagnantes
		options_gagnantes = request.form.getlist("options_gagnantes")

		for opt_id in options_gagnantes:
			valider_option_gagnante(opt_id, match_id)

		# Une fois les résultats saisis, on peut fermer le match
		fermer_match_officiellement(match_id)
		executer_settlement_match(match_id)

		flash("Résultats enregistrés et match clôturé !", "success")
		return redirect(url_for("matchs.show_edit_matchs"))

	return render_template("admin/matchs/cloturer_match.html", match=match_data, options=options)


@matchs_bp.route("/supprimer/<int:match_id>", methods=["POST"])
@admin_required
def supprimer_match_route(match_id):
	username = request.form.get("username").strip()
	password = request.form.get("password")

	if username != session["username"]:
		flash("Nom d'utilisateur incorrect !")
		return redirect(url_for("matchs.show_edit_matchs"))

	user = get_user_by_username(username)
	# Remplacez par votre logique de vérification (ex: check_password_hash)
	# Ici, je suppose une comparaison simple ou via une fonction dédiée
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

	if not role:
		flash("Choisissez le role !")
		return redirect(request.referrer)
	token = secrets.token_urlsafe(32)
	expiration = datetime.now() + timedelta(hours=48)

	# Appel d'une fonction SQL (à créer dans models/admin.py)
	# Elle insère : email, role, token, expiration et actif=0
	succes, message = creer_invitation_admin(email, role, token, expiration)

	# Lien à envoyer (en local pour tes tests)
	if succes:
		lien = url_for("admin.setup_staff", token=token, _external=True)

		succes, message = envoyer_invitation_admin(nom, email, lien)
		if succes:
			flash(
				f"Invitation envoyé à {nom} ! ({email}) pour le rôle : {role} !",
				"succes",
			)
		else:
			flash(message)
		return redirect(url_for("admin.staff"))
	else:
		flash(message)
		return redirect(url_for("admin.staff"))


@admin_bp.route("/setup_staff/<token>", methods=["GET", "POST"])  # Ajout du <token>
def setup_staff(token):
	if request.method == "GET":
		# 1. On cherche l'invitation par le TOKEN, pas par l'email
		invitation = get_invitation_by_token(token)  # À créer dans admin.py

		if not invitation:
			flash("Lien d'invitation invalide.")
			return redirect(url_for("home"))

		# 2. Vérification du délai de 48h
		# On convertit la chaîne de la BD en objet datetime
		expire_at = datetime.strptime(invitation["expiration"], "%Y-%m-%d %H:%M:%S.%f")
		if datetime.now() > expire_at:
			flash("Ce lien a expiré.")
			return redirect(url_for("home"))

			# ... (tes vérifications de mdp, username, etc.) ...

			# 3. Utilise l'email et le rôle qui viennent de l'invitation (sécurisé)
	invitation = get_invitation_by_token(token)
	email = invitation["email"]
	role = invitation["role"]

	# ... (logique d'ajout du parieur) ...

	donnees = request.form

	prenom = donnees.get("first_name", "").strip()
	nom = donnees.get("last_name", "").strip()
	username = donnees.get("username", "").strip()
	age = donnees.get("age", "")
	classe = "Direction"
	mdp = donnees.get("mdp", "")
	mdpConfirm = donnees.get("mdpConfirm")
	role = invitation["role"]
	rules = donnees.get("rules")

	# Vérifie si le champ contient UNIQUEMENT lettres, chiffres et _
	if not match(r"^[a-zA-Z0-9_]+$", username):
		usernameError = (
			"Le nom d'utilisateur ne peut contenir que des lettres, chiffres et underscores (_)"
		)
		return render_template("admin/setup_staff.html", error=usernameError)

	if len(prenom) > 20 or len(nom) > 20 or len(username) > 20:
		lenError = "Certains champs sont trop longs !"
		return render_template("admin/setup_staff.html", error=lenError)

	if len(mdp) < 8 or not mdp:
		mdpLenError = "Le mot de passe est trop court !"
		return render_template("admin/setup_staff.html", error=mdpLenError)

	if mdp != mdpConfirm:
		mdpError = "Les mots de passe ne correspondent pas !"
		return render_template("admin/setup_staff.html", error=mdpError)

	utilisateur = get_user_by_email(email)
	if utilisateur and utilisateur["email"] == email:
		emailError = "Cet email est déjà utilisé !"
		return render_template("admin/setup_staff.html", error=emailError)

	utilisateur = get_user_by_username(username)
	if utilisateur:
		usernameError = "Ce nom d'utilisateurest déjà pris !"
		return render_template("admin/setup_staff.html", error=usernameError)

	try:
		age = int(age)
		if age < 0 or age > 100:
			raise ValueError("Age non valide !")
	except ValueError:
		ageError = "Veuillez entrer un âge valide (entre 0 et 100 ans)."
		return render_template("admin/setup_staff.html", error=ageError)

	if not rules:
		rulesError = "Vous n'avez pas accepté les règles d'utilisation."
		return render_template("admin/setup_staff.html", error=rulesError)

	hashed_passeword = generate_password_hash(mdp)
	user = {
		"prenom": prenom,
		"nom": nom,
		"username": username,
		"email": email,
		"age": age,
		"classe": classe,
		"mdp": hashed_passeword,
		"role": role,
		"created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
	}
	ajouter_parieur(user)

	supprimer_invitation(token)
	session["username"] = username
	flash(f"Votre compte a été créé avec succès. Bienvenue Adm {prenom}", "succes")
	return redirect(url_for("home"))


@admin_bp.route("/mailbox", methods=["GET", "POST"])
@admin_required
def mailbox():
	if request.method == "GET":
		return render_template("admin/mailbox.html")
	donnees = request.form
	titre = donnees.get("titre").strip()
	message = donnees.get("message").strip()
	text_button = donnees.get("text_button").strip()
	lien = donnees.get("lien").strip()

	key = donnees.get("key").strip()
	result = donnees.get("result").strip()
	emails_envoyes = 0

	users = get_users(key, result)
	for user in users:
		succes, message = envoyer_notification_generale(
			user["prenom"], user["email"], titre, message, lien, text_button
		)
		if succes:
			emails_envoyes = emails_envoyes + 1
		else:
			error = message
	if not error:
		flash(f"Emails envoyés : {emails_envoyes} !")
	else:
		flash(f"Il y a eu une erreur lors de l'envoi : {error} ! Emails envoyés : {emails_envoyes}")
	return redirect(request.referrer)
