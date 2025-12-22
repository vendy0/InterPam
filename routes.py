
# Dans ton fichier principal
from admin_routes import admin_bp

app.register_blueprint(admin_bp)
from flask import Flask, render_template, request, redirect, url_for, session, flash
import re
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from data import (
    ajouter_parieur,
    recuperer_utilisateur_par_email,
    recuperer_utilisateur_par_username,
    ajouter_match,
    recuperer_matchs_complets,
    recuperer_matchs_en_cours,
    recuperer_programmes,
    placer_pari,
    obtenir_cotes_par_ids,
)
# Dans ton fichier principal
from admin_routes import admin_bp

app.register_blueprint(admin_bp)


app = Flask(__name__)

app.secret_key = "61e5e0e3df16e86a4957e6c22bc45190fc83bfae9516b771b7241baf55d"


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

    utilisateur = recuperer_utilisateur_par_email(
        email_username
    ) or recuperer_utilisateur_par_username(email_username)
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

    utilisateur = recuperer_utilisateur_par_email(email)
    if utilisateur and utilisateur["email"] == email:
        emailError = "Cet email est déjà utilisé !"
        return render_template("auth.html", error=emailError)

    utilisateur = recuperer_utilisateur_par_username(username)
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
        "solde": 0,
    }
    ajouter_parieur(user)
    flash("Votre compte a été créé avec succès.", "succes")
    session["username"] = username
    return redirect(url_for("home"))


# def est_admin():
#     if "username" not in session:
#         return False
#     user = recuperer_utilisateur_par_username(session["username"])
#     # On autorise tous les rôles administratifs
#     return user and user["role"] in ["super_admin", "admin", "statisticien"]


@app.route("/admin/dashboard")
def admin_dashboard():
    if not est_admin():
        flash("Accès interdit. Réservé au staff.", "error")
        return redirect(url_for("home"))

    return "Bienvenue sur le Panel Admin !"


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/home")
def home():
    if "username" in session:
        user = recuperer_utilisateur_par_username(session["username"])
        programmes = recuperer_programmes()
        return render_template("home.html", user=user, programmes=programmes)
    else:
        return redirect(url_for("index"))


# Dans routes.py
@app.route("/match/<int:match_id>")
def details_match(match_id):
    if "username" not in session:
        return redirect(url_for("login"))

    programmes = recuperer_programmes()
    match_trouve = next(
        (
            match
            for key, match in programmes.items()
            if match.get("match_id") == match_id
        ),
        None,
    )
    user = recuperer_utilisateur_par_username(session["username"])

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
        flash("Vous devez vous connecter !", "error")
        return redirect(url_for("login"))
    donnees = request.form
    try:
        match_id = int(donnees.get("match_id"))
        mise = float(donnees.get("mise", 0))
        options_choisies = []

        # On parcourt toutes les clés envoyées par le formulaire
        for cle, valeur in request.form.items():
            if cle not in ["match_id", "mise"]:
                options_choisies.append(valeur)  # valeur contient l'option_id

    except (ValueError, TypeError):
        flash("Données invalides", "error")
        return redirect(url_for("home"))

    try:
        user = recuperer_utilisateur_par_username(session["username"])
        date_pari = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Calcule du gain
        # gain_potentiel = mise

        # 1. On récupère les IDs proprement
        options_ids = [
            valeur
            for cle, valeur in request.form.items()
            if cle not in ["match_id", "mise"]
        ]

        if not options_ids:
            flash("Veuillez sélectionner au moins une option.", "error")
            return redirect(request.referrer)

        # 2. Le calcul du gain doit être HORS du bloc "if not options_ids"
        cote_totale = 1.0
        cotes = obtenir_cotes_par_ids(options_ids)

        for c in cotes:
            cote_totale *= c

        gain_potentiel = mise * cote_totale

        # Dans routes.py, à la fin de la route creer_fiche :
        succes, message = placer_pari(
            user["id"],
            match_id,
            mise,
            gain_potentiel,
            date_pari,
            options_ids,  # <-- On ajoute l'argument ici
        )

        if succes:
            flash(f"{message} {mise} HGT a été déduit de votre compte.", "succes")
            return redirect(url_for("home"))
        else:
            flash(message, "error")
            return redirect(request.referrer)

    except:
        return redirect(request.referrer)
