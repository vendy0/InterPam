# Dans ton fichier principal
from flask import Flask, render_template, request, redirect, url_for, session, flash
import re
from decimal import Decimal, ROUND_HALF_UP
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
    get_fiches_detaillees,
)
from admin_routes import admin_bp, users_bp, matchs_bp

app = Flask(__name__)
app.register_blueprint(admin_bp)
app.register_blueprint(users_bp)
app.register_blueprint(matchs_bp)

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
    email_username = donnees.get("email_username")
    mdp = donnees.get("mdp")

    utilisateur = get_user_by_email(email_username) or get_user_by_username(
        email_username
    )
    if utilisateur and check_password_hash(utilisateur["mdp"], mdp):
        session["username"] = utilisateur["username"]
        return redirect(url_for("home"))
    else:
        loginError = "Email ou mot de passe incorrect !"
        return render_template("auth.html", loginError=loginError)


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

    # Vérifie si le champ contient UNIQUEMENT lettres, chiffres et _
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        usernameError = "Le nom d'utilisateur ne peut contenir que des lettres, chiffres et underscores (_)"
        return render_template("auth.html", error=usernameError)

    if len(prenom) > 20 or len(nom) > 20 or len(username) > 20:
        lenError = "Certains champs sont trop longs !"
        return render_template("auth.html", error=lenError)

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
    session["username"] = username
    return redirect(url_for("home"))

    # def est_admin():
    #     if "username" not in session:
    #         return False
    #     user = get_utilisateur_par_username(session["username"])
    #     # On autorise tous les rôles administratifs
    #     return user and user["role"] in ["super_admin", "admin", "statisticien"]

    # @app.route("/admin/dashboard")
    # def admin_dashboard():
    #     if not est_admin():
    #         flash("Accès interdit. Réservé au staff.", "error")
    #         return redirect(url_for("home"))

    # return "Bienvenue sur le Panel Admin !"


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/home")
def home():
    if "username" in session:
        user = get_user_by_username(session["username"])
        programmes = get_programmes()
        return render_template("home.html", user=user, programmes=programmes)
    else:
        return redirect(url_for("index"))


# Dans routes.py
@app.route("/match/<int:match_id>")
def details_match(match_id):
    if "username" not in session:
        return redirect(url_for("login"))

    programmes = get_programmes()
    match_trouve = next(
        (
            match
            for key, match in programmes.items()
            if match.get("match_id") == match_id
        ),
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


@app.route("/create_fiche", methods=["POST"])
def creer_fiche():
    if "username" not in session:
        flash("Vous devez vous connecter", "error")
        return redirect(url_for("login"))

    try:
        donnees = request.form

        # Sécurité : Vérifier si match_id est présent
        raw_match_id = donnees.get("match_id")
        if not raw_match_id:
            flash("Match non identifié.", "error")
            return redirect(request.referrer)

        match_id = int(raw_match_id)

        # --- Lecture mise en Decimal ---
        # On nettoie la mise (remplace virgule par point)
        mise_str = donnees.get("mise", "0").replace(",", ".").strip()
        if not mise_str:
            mise_str = "0"

        mise_dec = Decimal(mise_str).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if mise_dec < Decimal("10.00"):
            flash("La mise minimum est de 10 HTG", "error")
            return redirect(request.referrer)

        user = get_user_by_username(session["username"])

        # --- Vérification solde ---
        if user["solde"] < mise_dec:
            flash("Solde insuffisant", "error")
            return redirect(request.referrer)

        # --- Options sélectionnées (CORRECTION ICI) ---
        options_ids = []
        for k, v in donnees.items():
            # On ignore les champs techniques 'match_id' et 'mise'
            if k in ("match_id", "mise"):
                continue

            # On ne garde que si la valeur est un nombre (l'ID de l'option)
            # Cela évite de planter sur le bouton 'submit' ou les tokens CSRF
            if v.isdigit():
                options_ids.append(int(v))

        if not options_ids:
            flash("Veuillez sélectionner au moins une option", "error")
            return redirect(request.referrer)

        # --- Calcul du gain ---
        cotes = obtenir_cotes_par_ids(options_ids)
        cote_totale = Decimal("1.00")
        for c in cotes:
            # Conversion explicite en string avant Decimal pour éviter les problèmes de float
            cote_totale *= Decimal(str(c))

        gain_dec = (mise_dec * cote_totale).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # --- Appel DATA ---
        succes, message = placer_pari(
            parieur_id=user["id"],
            match_id=match_id,
            mise_dec=mise_dec,
            gain_dec=gain_dec,
            date_pari=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            options_ids=options_ids,
        )

        flash(message, "success" if succes else "error")
        return redirect(url_for("home") if succes else request.referrer)

    except Exception as e:
        # Affiche l'erreur dans la console pour le développeur
        print(f"ERREUR CREATE FICHE : {e}")
        flash("Erreur technique lors de la création du pari.", "error")
        return redirect(request.referrer)


@app.route("/fiches")
def fiches():
    if "username" not in session:
        flash("Veuillez vous connecter !")
        return redirect(url_for("login"))
    user = get_user_by_username(session["username"])
    # On utilise la nouvelle fonction de regroupement
    mes_fiches = get_fiches_detaillees(user["id"])
    return render_template("fiches.html", fiches=mes_fiches)
