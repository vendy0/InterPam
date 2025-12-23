# routes.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
import re
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from data import (
	ajouter_parieur,
	get_user_by_email,
	get_user_by_username,
	ajouter_match,
	get_matchs_complets,
	get_matchs_en_cours,
	get_programmes,
	placer_pari,
	obtenir_cotes_par_ids,
	get_fiches,
	get_fiches_detaillees,
)
from admin_routes import admin_bp, users_bp

app = Flask(__name__)
app.register_blueprint(admin_bp)
app.register_blueprint(users_bp)

app.secret_key = "61e5e0e3df16e86a4957e6c22bc45190fc83bfae9516b771b7241baf55d"


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


@app.route("/about")
def about():
	return render_template("about.html")


@app.route("/register")
def register():
	if "username" in session:
		return redirect(url_for("home"))
	return render_template("auth.html", register="register")


@app.route("/login")
def login():
	if "username" in session:
		return redirect(url_for("home"))
	return render_template("auth.html")


@app.route("/logout")
def logout():
	session.pop("username", None)
	return redirect(url_for("login"))


@app.route("/traitement-login", methods=["POST", "GET"])
def traitementLogin():
	if request.method == "GET":
		return render_template("auth.html")

	donnees = request.form
	email_username = donnees.get("email_username")
	mdp = donnees.get("mdp")

	utilisateur = get_user_by_email(email_username) or get_user_by_username(email_username)

	if utilisateur and check_password_hash(utilisateur["mdp"], mdp):
		session["username"] = utilisateur["username"]
		return redirect(url_for("home"))
	else:
		loginError = "Email ou mot de passe incorrect !"
		return render_template("auth.html", loginError=loginError)


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

	if not re.match(r"^[a-zA-Z0-9_]+$", username):
		error = "Le nom d'utilisateur ne peut contenir que des lettres, chiffres et underscores (_)"
		return render_template("auth.html", error=error)

	if len(prenom) > 20 or len(nom) > 20 or len(username) > 20:
		return render_template("auth.html", error="Certains champs sont trop longs !")

	if len(mdp) < 8 or not mdp:
		return render_template("auth.html", error="Le mot de passe est trop court !")

	if mdp != mdpConfirm:
		return render_template("auth.html", error="Les mots de passe ne correspondent pas !")

	if get_user_by_email(email):
		return render_template("auth.html", error="Cet email est déjà utilisé !")

	if get_user_by_username(username):
		return render_template("auth.html", error="Ce nom d'utilisateur est déjà pris !")

	try:
		age = int(age)
		if age < 0 or age > 100:
			raise ValueError()
	except ValueError:
		return render_template("auth.html", error="Veuillez entrer un âge valide.")

	if not rules:
		return render_template("auth.html", error="Vous n'avez pas accepté les règles.")

	hashed_password = generate_password_hash(mdp)

	user = {
		"prenom": prenom,
		"nom": nom,
		"username": username,
		"email": email,
		"age": age,
		"classe": classe,
		"mdp": hashed_password,
		"created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
		"solde": 100000,
	}

	ajouter_parieur(user)
	flash("Votre compte a été créé avec succès.", "succes")
	session["username"] = username
	return redirect(url_for("home"))


@app.route("/home")
def home():
	if "username" in session:
		programmes = get_programmes()
		return render_template("home.html", programmes=programmes)
	return redirect(url_for("index"))


@app.route("/match/<int:match_id>")
def details_match(match_id):
	if "username" not in session:
		return redirect(url_for("login"))

	programmes = get_programmes()
	match_trouve = next((m for k, m in programmes.items() if m.get("match_id") == match_id), None)
	user = get_user_by_username(session["username"])

	if not match_trouve:
		flash("Match introuvable !", "error")
		return redirect(url_for("home"))

	categories_dict = {}
	for opt in match_trouve["options"]:
		cat = opt["categorie"]
		if cat not in categories_dict:
			categories_dict[cat] = []
		categories_dict[cat].append(opt)

	return render_template(
		"details_match.html", match=match_trouve, user=user, categories=categories_dict
	)


@app.route("/create_fiche", methods=["POST"])
def creer_fiche():
	if "username" not in session:
		flash("Vous devez vous connecter !", "error")
		return redirect(url_for("login"))

	donnees = request.form

	# ---- 1. Lecture & validation de la mise (Decimal) ----
	try:
		match_id = int(donnees.get("match_id"))

		mise_dec = Decimal(donnees.get("mise", "0").replace(",", ".").strip())

		if mise_dec < Decimal("10"):
			flash("La mise minimum est de 10 HTG", "error")
			return redirect(request.referrer)

		# Conversion UNIQUE vers centimes
		mise_centime = int((mise_dec * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

	except (ValueError, TypeError, InvalidOperation):
		flash("Montant de la mise invalide", "error")
		return redirect(request.referrer)

	# ---- 2. Vérifications utilisateur ----
	try:
		user = get_user_by_username(session["username"])
		date_pari = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

		# solde utilisateur = centimes
		if user["solde"] < mise_centime:
			flash("Votre solde est insuffisant !", "error")
			return redirect(request.referrer)

		# ---- 3. Options sélectionnées ----
		options_ids = [
			int(valeur) for cle, valeur in donnees.items() if cle not in ["match_id", "mise"]
		]

		if not options_ids:
			flash("Veuillez sélectionner au moins une option.", "error")
			return redirect(request.referrer)

		# ---- 4. Calcul du gain (Decimal) ----
		cotes = obtenir_cotes_par_ids(options_ids)

		cote_totale = Decimal("1.00")
		for c in cotes:
			cote_totale *= Decimal(str(c))

		gain_potentiel_dec = (mise_dec * cote_totale).quantize(
			Decimal("0.01"), rounding=ROUND_HALF_UP
		)

		# Conversion UNIQUE vers centimes
		gain_potentiel_centime = int(
			(gain_potentiel_dec * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
		)

		# ---- 5. Envoi à la BDD (CENTIMES UNIQUEMENT) ----
		succes, message = placer_pari(
			parieur_id=user["id"],
			match_id=match_id,
			mise_c=mise_centime,
			gain_c=gain_potentiel_centime,
			date_pari=date_pari,
			options_ids=options_ids,
		)

		if succes:
			flash(f"{message} {mise_dec} HTG ont été déduits de votre compte.", "success")
			return redirect(url_for("home"))

		flash(message, "error")
		return redirect(request.referrer)

	except Exception as e:
		flash("Il y a eu une erreur lors de la création de la fiche !", "error")
		return redirect(request.referrer)


@app.route("/fiches")
def fiches():
	if "username" not in session:
		flash("Veuillez vous connecter !")
		return redirect(url_for("login"))

	user = get_user_by_username(session["username"])
	mes_fiches = get_fiches_detaillees(user["id"])
	return render_template("fiches.html", fiches=mes_fiches)
