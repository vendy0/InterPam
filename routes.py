# Dans ton fichier principal
import os
from dotenv import load_dotenv
from flask import (
	Flask,
	render_template,
	request,
	redirect,
	url_for,
	session,
	flash,
	send_from_directory,
)
from re import match as re_match
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import json
from admin_routes import admin_bp, users_bp, matchs_bp
from models.match import *
from models.user import *
from models.bet import *
from models.emails import *

app = Flask(__name__)
app.register_blueprint(admin_bp)
app.register_blueprint(users_bp)
app.register_blueprint(matchs_bp)


# Utilise les variables chargées
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY_SESSION")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["DB_PATH"] = os.getenv("DB_PATH")

# Sécurité supplémentaire pour les cookies de session
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.secret_key = os.getenv("SECRET_KEY")


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


@app.context_processor
def inject_user():
	user = None
	if "username" in session:
		user = get_user_by_username(session["username"])
	return dict(current_user=user)


app.jinja_env.globals.update(set_date=set_date)



@app.template_filter("devise")
def format_devise(valeur_centimes):
	return "{:,.2f} HTG".format(valeur_centimes / 100)


@app.route("/")
def index():
	return render_template("index.html")


@app.route("/register")
def register():
	if "username" in session:
		return redirect(url_for("home"))
	else:
		return render_template("auth.html", register="register")


@app.route("/login")
def login():
	if "username" in session:
		return redirect(url_for("home"))
	else:
		return render_template("auth.html")


@app.route("/logout")
def logout():
	session.pop("username", None)
	return redirect(url_for("login"))


# Connexion
@app.route("/traitement-login", methods=["POST", "GET"])
def traitementLogin():
	if request.method == "GET":
		return render_template("auth.html")
	donnees = request.form
	email_username = donnees.get("email_username").strip()
	mdp = donnees.get("mdp")

	utilisateur = get_user_by_email(email_username) or get_user_by_username(email_username)
	if utilisateur and check_password_hash(utilisateur["mdp"], mdp):
		actif = bool(utilisateur["actif"])
		if not actif:
			banError = "Ce compte a été suspendu !"
			return render_template("auth.html", loginError=banError)
		session["username"] = utilisateur["username"]
		return redirect(url_for("home"))
	else:
		loginError = "Email ou mot de passe incorrect !"
		return render_template("auth.html", loginError=loginError)


def valider_nom_prenom(entree):
	# On définit le pattern
	pattern = r"^[a-zA-ZàâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ\s'-]+$"

	# On vérifie la correspondance
	if re_match(pattern, entree):
		return True
	return False


# Inscription
@app.route("/traitement-register", methods=["POST", "GET"])
def traitementRegister():
	if request.method == "GET":
		return render_template("auth.html")
	donnees = request.form
	prenom = donnees.get("first_name", "").strip()
	nom = donnees.get("last_name", "").strip()
	username = donnees.get("username", "").strip()
	email = donnees.get("email", "").strip()
	age = donnees.get("age", "")
	classe = donnees.get("classe", "")
	mdp = donnees.get("mdp", "")
	mdpConfirm = donnees.get("mdpConfirm")
	rules = donnees.get("rules")

	confirm_prenom = valider_nom_prenom(prenom)
	confirm_nom = valider_nom_prenom(nom)

	if not confirm_prenom or not confirm_nom:
		nameError = "Le nom et le prénom ne doivent contenir que des lettres, des espaces, des tirets ou des apostrophes (ex: Jean-Pierre, D'Olier)."
		return render_template("auth.html", error=nameError)

	# Vérifie si le champ contient UNIQUEMENT lettres, chiffres et _
	if not re_match(r"^[a-zA-Z0-9_]+$", username):
		usernameError = (
			"Le nom d'utilisateur ne peut contenir que des lettres, chiffres et underscores (_)"
		)
		return render_template("auth.html", error=usernameError)

	if len(prenom) > 20 or len(nom) > 20 or len(username) > 20:
		lenError = "Certains champs sont trop longs !"
		return render_template("auth.html", error=lenError)
		
	if not classe:
		classeError="Vous n'avez pas séléctionné la classe !"
		return render_template("auth.html", error=classeError)

	if len(mdp) < 8 or not mdp:
		mdpLenError = "Le mot de passe est trop court !"
		return render_template("auth.html", error=mdpLenError)

	if mdp != mdpConfirm:
		mdpError = "Les mots de passe ne correspondent pas !"
		return render_template("auth.html", error=mdpError)

	utilisateur = get_user_by_email(email)
	if utilisateur and utilisateur["email"] == email:
		emailError = "Cet email est déjà utilisé !"
		return render_template("auth.html", error=emailError)

	utilisateur = get_user_by_username(username)
	if utilisateur:
		usernameError = "Ce nom d'utilisateurest déjà pris !"
		return render_template("auth.html", error=usernameError)

	try:
		age = int(age)
		if age < 0 or age > 100:
			raise ValueError("Age non valide !")
	except ValueError:
		ageError = "Veuillez entrer un âge valide (entre 0 et 100 ans)."
		return render_template("auth.html", error=ageError)

	if not rules:
		rulesError = "Vous n'avez pas accepté les règles d'utilisation."
		return render_template("auth.html", error=rulesError)

	hashed_passeword = generate_password_hash(mdp)

	user = {
		"prenom": prenom,
		"nom": nom,
		"username": username,
		"email": email,
		"age": age,
		"classe": classe,
		"mdp": hashed_passeword,
		"created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
	}
	ajouter_parieur(user)
	flash("Votre compte a été créé avec succès.", "succes")
	welcome_email(prenom, email, url_for("home"))
	session["username"] = username
	return redirect(url_for("home"))


@app.route("/about")
def about():
	return render_template("about.html")


@app.route("/home")
def home():
	if "username" in session:
		user = get_user_by_username(session["username"])
		programmes = get_programmes()
		return render_template("home.html", user=user, programmes=programmes)
	return redirect(url_for("index"))


@app.route("/save-subscription", methods=["POST"])
def save_subscription_route():
	subscription_data = request.json
	user = get_user_by_username(session["username"])
	user_id = user["id"]
	# C'est le JSON envoyé par le JS
	(save_subscription(json.dumps(subscription_data), user_id))


# Dans ton app.py
@app.route("/sw.js")
def serve_sw():
	return send_from_directory("static", "sw.js", mimetype="application/javascript")


# Dans routes.py
@app.route("/match/<int:match_id>")
def details_match(match_id):
	if "username" not in session:
		return redirect(url_for("login"))

	programmes = get_programmes()
	match_trouve = next(
		(match for key, match in programmes.items() if match.get("match_id") == match_id),
		None,
	)
	user = get_user_by_username(session["username"])

	if not match_trouve:
		flash("Match introuvable !", "error")
		return redirect(url_for("home"))

	# Dans routes.py -> details_match

	categories_dict = {}
	for opt in match_trouve["options"]:
		cat = opt["categorie"]
		if cat not in categories_dict:
			categories_dict[cat] = []

		# CETTE LIGNE DOIT ÊTRE INDENTÉE (DÉCALÉE) DANS LA BOUCLE FOR
		categories_dict[cat].append(opt)

	return render_template(
		"details_match.html", match=match_trouve, user=user, categories=categories_dict
	)


"""
========================================
* : GESTION DES PARIS-------------------
========================================
"""


@app.route("/ajouter_au_ticket", methods=["POST"])
def ajouter_au_ticket():
	"""Ajoute une sélection au panier (session). Écrase si le match existe déjà."""
	if "username" not in session:
		return redirect(url_for("login"))

	match_id = request.form.get("match_id")
	# On cherche l'option cochée dans le formulaire
	# Le formulaire envoie dynamiquement le nom de la catégorie, il faut donc itérer
	option_id = None
	for key, value in request.form.items():
		# On ignore le match_id et les champs techniques, on cherche l'ID de l'option (numérique)
		if key != "match_id" and value.isdigit():
			option_id = int(value)
			break

	if not match_id or not option_id:
		flash("Veuillez sélectionner une cote.", "error")
		return redirect(request.referrer)

	# Initialisation du panier s'il n'existe pas
	if "ticket" not in session:
		session["ticket"] = {}

	# RÈGLE D'OR : Une seule option par match.
	# On utilise match_id comme CLÉ du dictionnaire.
	# Si l'utilisateur parie à nouveau sur ce match, l'ancienne valeur est écrasée.
	session["ticket"][match_id] = option_id
	session.modified = True  # Important pour dire à Flask de sauvegarder la session

	flash("Ajouté au ticket !", "succes")
	return redirect(request.referrer)  # On reste sur la page ou on va au panier ? Au choix.


@app.route("/mon_ticket")
def mon_ticket():
	"""Affiche le récapitulatif avant validation"""
	if "username" not in session:
		return redirect(url_for("login"))

	ticket = session.get("ticket", {})
	user = get_user_by_username(session["username"])

	options_ids = list(ticket.values())
	details = get_details_options_panier(options_ids)

	# Calcul de la cote totale
	cote_totale = Decimal("1")
	for ligne in details:
		cote_totale *= Decimal(str(ligne["cote"]))

	return render_template("ticket.html", selections=details, cote_totale=cote_totale, user=user)


@app.route("/supprimer_du_ticket/<match_id>")
def supprimer_du_ticket(match_id):
	"""Retire un match spécifique du ticket"""
	if "ticket" in session:
		# On retire la clé correspondant au match
		session["ticket"].pop(match_id, None)
		session.modified = True
	return redirect(url_for("mon_ticket"))


@app.route("/vider_ticket")
def vider_ticket():
	session.pop("ticket", None)
	return redirect(url_for("home"))


@app.route("/valider_ticket", methods=["POST"])
def valider_ticket():
	if "username" not in session:
		return redirect(url_for("login"))

	ticket = session.get("ticket", {})
	if not ticket:
		flash("Votre ticket est vide.", "error")
		return redirect(url_for("home"))

	options_ids = list(ticket.values())

	# --- NOUVELLE VÉRIFICATION DE SÉCURITÉ ---
	if not verifier_matchs_ouverts(options_ids):
		# On identifie les matchs qui ne sont plus ouverts pour nettoyer le ticket (optionnel)
		# Mais le plus important est de bloquer le pari
		flash(
			"Certains matchs de votre ticket ne sont plus disponibles (matchs commencés ou fermés).",
			"error",
		)
		return redirect(url_for("mon_ticket"))
	# -----------------------------------------

	user = get_user_by_username(session["username"])
	mise_str = request.form.get("mise", "0").replace(",", ".")

	try:
		mise_dec = Decimal(mise_str).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
	except:
		mise_dec = Decimal("0.00")

	if mise_dec < Decimal("10.00"):
		flash("Mise minimum : 10 HTG", "error")
		return redirect(url_for("mon_ticket"))

	if user["solde"] < mise_dec:
		flash("Solde insuffisant.", "error")
		return redirect(url_for("mon_ticket"))

	# Recalculer la cote totale côté serveur (sécurité)
	options_ids = list(ticket.values())
	details = get_details_options_panier(options_ids)

	if len(details) != len(options_ids):
		flash("Une des options n'est plus disponible.", "error")
		return redirect(url_for("mon_ticket"))

	cote_totale = Decimal("1.00")
	for d in details:
		cote_totale *= Decimal(str(d["cote"]))

	gain_dec = (mise_dec * cote_totale).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

	# Enregistrement en BDD
	# On prend le premier match_id de la liste comme référence "principale"
	# ou on adapte placer_pari pour gérer le NULL si tu préfères,
	# mais ici on va garder la logique actuelle : on passe le premier ID de match pour la forme,
	# mais ce qui compte ce sont les options_ids.
	first_match_id = details[0]["match_id"]

	succes, msg = placer_pari(
		parieur_id=user["id"],
		match_id=first_match_id,  # Technique: on lie au moins à un match
		mise_dec=mise_dec,
		gain_dec=gain_dec,
		date_pari=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
		options_ids=options_ids,
	)

	if succes:
		session.pop("ticket", None)  # On vide le panier après succès
		flash(f"Pari validé ! Gain potentiel : {gain_dec} HTG", "succes")
		return redirect(url_for("fiches"))
	else:
		flash(msg, "error")
		return redirect(url_for("mon_ticket"))


@app.route("/fiches")
def fiches():
	if "username" not in session:
		return redirect(url_for("login"))
	user = get_user_by_username(session["username"])
	# On utilise la nouvelle fonction de regroupement
	mes_fiches = get_fiches_detaillees(user["id"])
	return render_template("fiches.html", fiches=mes_fiches)
