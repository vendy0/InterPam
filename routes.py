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
from dotenv import load_dotenv
load_dotenv() 
from re import match as re_match
import uuid
from functools import wraps
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import json

from admin_routes import admin_bp, users_bp, matchs_bp

from database.setup import initialiser_bdd
from models.match import *
from models.user import *
from models.bet import *
from models.emails import *
from models.transaction import *
from models.config import get_config, mouvement_caisse

app = Flask(__name__)

initialiser_bdd()

app.register_blueprint(admin_bp)
app.register_blueprint(users_bp)
app.register_blueprint(matchs_bp)


# Utilise les variables chargées
app.config["SECRET_KEY_SESSION"] = os.getenv("SECRET_KEY_SESSION")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["DB_PATH"] = os.getenv("DB_PATH")
app.config["EMAIL_ADRESSE"] = os.getenv("EMAIL_ADRESSE")
app.config["VAPID_PRIVATE_KEY"] = os.getenv("VAPID_PRIVATE_KEY")
app.config["VAPID_SUBJECT"] = os.getenv("VAPID_SUBJECT")

# Sécurité supplémentaire pour les cookies de session
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True  # si HTTPS


# --- AJOUT À FAIRE ICI ---
# Définit la durée de la session à 30 jours (ou 365 pour un an)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)


app.secret_key = os.getenv("SECRET_KEY_SESSION")


def active_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" in session:
            user = get_user_by_username(session["username"])
            if not user or not bool(user["actif"]):
                session.clear()
                flash("Votre compte a été suspendu.", "error")
                return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


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


@app.context_processor
def inject_globals():
    user = None
    if "username" in session:
        user = get_user_by_username(session["username"])

    def format_money(valeur):
        try:
            # On convertit en float pour que le formateur puisse traiter les décimales
            num = float(valeur)
            # ':g' retire les zéros inutiles après la virgule (ex: 100.0 -> 100)
            # '{:,}' gère les milliers, que l'on remplace ensuite par un espace
            return "{:,.10g}".format(num).replace(",", " ")
        except (ValueError, TypeError):
            return "0"

    conf = get_config()

    # On injecte tout dans le dictionnaire
    return dict(
        current_user=user,
        set_date=set_date,
        format_money=format_money,
        frais_retrait=conf["frais_retrait"],
        config_global=conf,
    )


def format_money(valeur):
    try:
        # On convertit en float pour que le formateur puisse traiter les décimales
        num = float(valeur)
        # ':g' retire les zéros inutiles après la virgule (ex: 100.0 -> 100)
        # '{:,}' gère les milliers, que l'on remplace ensuite par un espace
        return "{:,.10g}".format(num).replace(",", " ")
    except (ValueError, TypeError):
        return "0"


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
    email_username = clean_input(donnees.get("email_username"))
    mdp = donnees.get("mdp")
    remember = True if request.form.get("remember", "") else False
    #
    # 	if not email_username or not mdp:
    # 		return render_template("auth.html", loginError="Tous les champs doivent être remplis !")

    utilisateur = get_user_by_email(email_username.lower()) or get_user_by_username(
        email_username
    )
    if utilisateur and check_password_hash(utilisateur["mdp"], mdp):
        if not bool(utilisateur["actif"]):
            return render_template("auth.html", loginError="Ce compte a été suspendu !")

        session.clear()  # IMPORTANT
        session["username"] = utilisateur["username"]

        if remember:
            session.permanent = True
        else:
            session.permanent = False

        return redirect(url_for("home"))
    else:
        loginError = "Identifiants incorrect !"
        return render_template("auth.html", loginError=loginError)


def valider_nom_prenom(entree):
    # On définit le pattern
    pattern = r"^[a-zA-ZàâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ\s'.-]+$"
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
    prenom = clean_input(donnees.get("first_name", ""))
    nom = clean_input(donnees.get("last_name", ""))
    username = clean_input(donnees.get("username", ""))
    email = clean_input(donnees.get("email", "").lower())
    age = donnees.get("age", "")
    classe = clean_input(donnees.get("classe", ""))
    mdp = clean_input(donnees.get("mdp_inscription", ""))
    mdpConfirm = clean_input(donnees.get("mdp_confirm"))
    rules = donnees.get("rules", False)

    if not all([prenom, nom, username, email, age, classe, mdp, mdpConfirm]):
        return render_template("auth.html", error="Tous les champs sont obligatoire !")

    confirm_prenom = valider_nom_prenom(prenom)
    confirm_nom = valider_nom_prenom(nom)

    if not confirm_prenom or not confirm_nom:
        nameError = "Le nom et le prénom ne doivent contenir que des lettres, des espaces, des tirets ou des apostrophes (ex: Jean-Pierre, D'Olier)."
        return render_template("auth.html", error=nameError)

    # Vérifie si le champ contient UNIQUEMENT lettres, chiffres et _
    if not re_match(r"^[a-zA-Z0-9_]+$", username):
        usernameError = "Le nom d'utilisateur ne peut contenir que des lettres, chiffres et underscores (_)"
        return render_template("auth.html", error=usernameError)

    if len(prenom) > 20 or len(nom) > 20 or len(username) > 20:
        lenError = "Certains champs sont trop longs !"
        return render_template("auth.html", error=lenError)

    if not classe:
        classeError = "Vous n'avez pas séléctionné la classe !"
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

    if check_pending_duplicates(username, email):
        return render_template(
            "auth.html",
            error="Ce compte est en attente de validation. Vérifiez vos emails.",
        )

    hashed_password = generate_password_hash(mdp)

    # 1. Générer le token
    token = secrets.token_urlsafe(32)
    expiration = datetime.now() + timedelta(hours=24)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 2. Préparer les données
    user_data = {
        "prenom": prenom,
        "nom": nom,
        "username": username,
        "email": email,
        "age": age,
        "classe": classe,
        "mdp": hashed_password,
        "created_at": created_at,
    }

    # 3. Sauvegarder dans pending_registrations
    if save_pending_registration(user_data, token, expiration):
        # 4. Envoyer l'email
        lien = url_for("confirm_email", token=token, _external=True)
        # Assurez-vous d'importer envoyer_mail_verification depuis vos modèles
        try:
            envoyer_mail_verification(prenom, email, lien)
        except Exception as e:
            print(e)
            flash("Erreur lors de l'envoi de l'email.", "error")

        return "Inscription enregistrée ! Un email de confirmation vous sera envoyé dans quelques minutes."
    # On reste sur la page de login avec le message
    else:
        return render_template(
            "auth.html", error="Erreur technique lors de l'inscription."
        )


@app.route("/confirm-email/<token>")
def confirm_email(token):
    # 1. Récupérer les données temporaires
    pending_user = get_pending_by_token(token)

    if not pending_user:
        flash("Lien de confirmation invalide ou déjà utilisé.", "error")
        return redirect(url_for("login"))

    # 2. Vérifier l'expiration
    expire_at = datetime.strptime(pending_user["expiration"], "%Y-%m-%d %H:%M:%S.%f")
    if datetime.now() > expire_at:
        delete_pending(token)  # On nettoie
        flash("Ce lien a expiré. Veuillez vous réinscrire.", "error")
        return redirect(url_for("register"))

    # 3. Transférer vers la table principale (parieurs)
    # On nettoie le dictionnaire pour enlever id, token et expiration qui ne vont pas dans 'parieurs'
    final_user_data = {
        "prenom": pending_user["prenom"],
        "nom": pending_user["nom"],
        "username": pending_user["username"],
        "email": pending_user["email"],
        "age": pending_user["age"],
        "classe": pending_user["classe"],
        "mdp": pending_user["mdp"],  # Déjà hashé
        "created_at": pending_user["created_at"],
        "role": "parieur",  # Par défaut
    }

    ajouter_parieur(final_user_data)

    # 4. Supprimer de la table temporaire
    delete_pending(token)

    # 5. Connecter l'utilisateur (Optionnel, ou juste rediriger vers login)
    session["username"] = final_user_data["username"]
    session.permanent = False

    flash("Votre compte a été activé avec succès ! Bienvenue.", "success")
    welcome_email(
        final_user_data["prenom"],
        final_user_data["email"],
        url_for("home", _external=True),
    )

    session.permanent = False
    session["username"] = pending_user["username"]
    return redirect(url_for("home"))


@app.route("/forget_password", methods=["GET", "POST"])
def forget_password_route():
    email = clean_input(request.form.get("forget_email").lower())
    if not email:
        forgetError = "Veuillez rentrer un email valide !"
        return render_template("auth.html", forgetError=forgetError)

    user = get_user_by_email(email)
    if not user:
        forgetError = "Aucun compte n'est encore lié à cet email !"
        return render_template("auth.html", forgetError=forgetError)
    token = secrets.token_urlsafe(32)
    expiration = datetime.now() + timedelta(hours=24)
    success = save_recuperation(email, token, expiration)
    if not success:
        return render_template(
            "auth.html",
            forgetError="Il y a eu une erreur lors de la réinitialisation. Veuillez contacter l'assistance si l'erreur persiste.",
        )
    lien = url_for("reset_password_route", token=token, _external=True)
    success_mail, message = password_reset_email(user["prenom"], email, lien)
    return "Un email de confirmation vous sera envoyé dans quelques minutes."


@app.route("/Conditions")
def legal():
    return render_template("legal.html")


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password_route(token):
    recuperation = get_recuperation_by_token(token)
    if not recuperation:
        return "<h1>Lien invalide !</h1>"
    # Vérification du délai de 48h
    expire_at = datetime.strptime(recuperation["expiration"], "%Y-%m-%d %H:%M:%S.%f")
    if datetime.now() > expire_at:
        flash("Ce lien a expiré.", "error")
        return "<h1>Ce lien a expiré !</h1>"

    if request.method == "GET":
        return render_template("reset_password.html", token=token)

    mdp = request.form.get("password")
    confirm_mdp = request.form.get("confirm_password")
    if not mdp or not confirm_mdp:
        return render_template(
            "reset_password.html",
            resetError="Vous devez remplire les deux champs de mot de passe !",
        )

    if not mdp or len(mdp) < 8:
        mdpLenError = "Le mot de passe est trop court !"
        return render_template("reset_password.html", resetError=mdpLenError)

    if mdp != confirm_mdp:
        mdpError = "Les mots de passe ne correspondent pas !"
        return render_template("reset_password.html", resetError=mdpError)

    user = get_user_by_email(recuperation["email"])

    hashed_password = generate_password_hash(mdp)
    if reset_password(recuperation["email"], hashed_password):
        message = "Votre mot de passe InterPam vient d'être modifier. Cliquer ici pour acceder à InterPam dès maintenant :"
        lien = url_for("home", _external=True)

        envoyer_notification_generale(
            user["prenom"],
            recuperation["email"],
            "Réinitialisation réussie",
            message,
        )
        session.permanent = False
        session["username"] = user["username"]
        return redirect(url_for("home"))
    else:
        return "<h1>Il y a eu une erreur lors de la réinitialisation du mot de passe !</h1>"


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/home")
@active_required
def home():
    if "username" in session:
        user = get_user_by_username(session["username"])
        programmes = get_programmes()
        return render_template("home.html", user=user, programmes=programmes)
    return redirect(url_for("index"))


@app.route("/send_message", methods=["POST"])
@active_required
def send_message_route():
    if "username" not in session:
        return redirect(url_for("login"))
    user = get_user_by_username(session["username"])
    message_sent = request.form.get("message")
    if len(message_sent) >= 410:
        flash("Message trop long !", "error")
        return redirect(request.referrer)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if send_message(user["id"], message_sent, created_at):
        flash("Message envoyé !", "success")
        sup = get_users("role", "super_admin")[0]
        if sup["push_subscription"]:
            envoyer_push_notification(
                sup["push_subscription"],
                "Nouveau message",
                f"{user['prenom']} : {message_sent}",
                url=url_for("admin.messagerie", _external=True),
            )
        return redirect(request.referrer)
    else:
        flash("Il y a eu une erreur lors de l'envoi !", "error")
        return redirect(request.referrer)


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
@active_required
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


"""
========================================
* : GESTION DES PARIS-------------------
========================================
"""


@app.route("/ajouter_au_ticket", methods=["POST"])
@active_required
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

    flash("Ajouté au ticket ! \n N'oubliez pas de valider le ticket.", "success")
    return redirect(
        url_for("home")
    )  # On reste sur la page ou on va au panier ? Au choix.


@app.route("/mon_ticket")
@active_required
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
    # On génère un token unique pour ce chargement de page "mon_ticket"
    token_pari = str(uuid.uuid4())
    session["token_pari"] = token_pari
    return render_template(
        "ticket.html",
        selections=details,
        cote_totale=cote_totale,
        user=user,
        token=token_pari,
    )


@app.route("/supprimer_du_ticket/<match_id>")
@active_required
def supprimer_du_ticket(match_id):
    """Retire un match spécifique du ticket"""
    if "ticket" in session:
        # On retire la clé correspondant au match
        session["ticket"].pop(match_id, None)
        session.modified = True
    return redirect(url_for("mon_ticket"))


@app.route("/vider_ticket")
@active_required
def vider_ticket():
    session.pop("ticket", None)
    return redirect(url_for("home"))


@app.route("/valider_ticket", methods=["POST"])
@active_required
def valider_ticket():
    if "username" not in session:
        return redirect(url_for("login"))

    # --- SÉCURITÉ ANTI-REPLAY ---
    token_form = request.form.get("token")
    token_session = session.get("token_pari")

    # Si pas de token ou token différent -> On bloque
    if not token_form or token_form != token_session:
        flash("Transaction annulée : double-clic détecté ou page expirée.", "error")
        # On redirige vers l'accueil ou le ticket vide pour éviter de re-submit
        return redirect(url_for("home"))

    # On supprime le token pour qu'il ne soit plus jamais réutilisable
    session.pop("token_pari", None)
    # ----------------------------

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

    # 1. Récupérer Config
    config = get_config()
    mise_min = config["mise_min"]
    mise_max = config["mise_max"]

    user = get_user_by_username(session["username"])
    mise_str = request.form.get("mise", "0").replace(",", ".")

    try:
        mise_dec = Decimal(mise_str).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except:
        mise_dec = Decimal("0.00")

    if user["solde"] < mise_dec:
        flash("Solde insuffisant.", "error")
        return redirect(url_for("mon_ticket"))

        # 2. Vérification Min/Max
    if mise_dec < Decimal(str(mise_min)) or mise_dec > Decimal(str(mise_max)):
        flash(
            f"La mise doit être comprise entre {format_money(mise_min)} et {format_money(mise_max)} HTG.",
            "error",
        )
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

    gain_dec = (mise_dec * cote_totale).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    # 3. Vérification Solvabilité Caisse
    if config["caisse_solde"] < gain_dec:
        flash(
            "Impossible de placer ce pari : Plafond de trésorerie atteint pour ce gain potentiel. Essayez une mise plus petite.",
            "error",
        )
        return redirect(url_for("mon_ticket"))
    # Enregistrement en BDD
    # On prend le premier match_id de la liste comme référence "principale"
    # ou on adapte placer_pari pour gérer le NULL si tu préfères,
    # mais ici on va garder la logique actuelle : on passe le premier ID de match pour la forme,
    # mais ce qui compte ce sont les options_ids.
    first_match_id = details[0]["match_id"]

    success, msg = placer_pari(
        parieur_id=user["id"],
        match_id=first_match_id,  # Technique: on lie au moins à un match
        mise_dec=mise_dec,
        gain_dec=gain_dec,
        date_pari=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        options_ids=options_ids,
    )

    if success:
        mouvement_caisse(gain_dec, "sub")
        session.pop("ticket", None)  # On vide le panier après succès
        flash(f"Pari validé ! Gain potentiel : {gain_dec} HTG", "success")
        return redirect(url_for("fiches"))
    else:
        flash(msg, "error")
        return redirect(url_for("mon_ticket"))


@app.route("/fiches")
@active_required
def fiches():
    if "username" not in session:
        return redirect(url_for("login"))
    user = get_user_by_username(session["username"])
    # On utilise la nouvelle fonction de regroupement
    mes_fiches = get_fiches_detaillees(user["id"])
    return render_template("fiches.html", fiches=mes_fiches)


# ... (imports existants)


# === Route pour l'Historique des Résultats ===
@app.route("/resultats")
@active_required
def resultats():
    if "username" not in session:
        return redirect(url_for("login"))

    user = get_user_by_username(session["username"])
    # ICI : On appelle la nouvelle fonction globale
    matchs_termines = get_tous_les_resultats(user["id"])

    return render_template("resultats.html", matchs=matchs_termines)


@app.route("/portefeuille", methods=["GET"])
@active_required
def portefeuille():
    if "username" not in session:
        return redirect(url_for("login"))

    user = get_user_by_username(session["username"])
    historique = get_user_transactions(user["id"])

    return render_template("wallet.html", transactions=historique)


@app.route("/demande-depot", methods=["POST"])
@active_required
def demande_depot():
    if "username" not in session:
        return redirect(url_for("login"))

    user = get_user_by_username(session["username"])
    try:
        montant = float(request.form.get("montant", "0").replace(",", "."))
        telephone = request.form.get("telephone").strip()
        moncash_id = request.form.get("moncash_id").strip()

        if montant <= 0:
            flash("Le montant doit être positif.", "error")
            return redirect(url_for("portefeuille"))

        if not telephone or not moncash_id:
            flash("Veuillez remplir tous les champs MonCash.", "error")
            return redirect(url_for("portefeuille"))

        # On crée juste la demande, pas de mouvement d'argent immédiat
        success, msg = create_transaction(
            user["id"], "depot", montant, telephone, moncash_id
        )

        if success:
            flash("Demande de dépôt envoyée ! En attente de validation.", "success")
        else:
            flash(msg, "error")

    except ValueError:
        flash("Montant invalide.", "error")

    return redirect(url_for("portefeuille"))


# 2. Mise à jour de la route demande_retrait pour calculer les frais
@app.route("/demande-retrait", methods=["POST"])
@active_required
def demande_retrait():
    if "username" not in session:
        return redirect(url_for("login"))

    user = get_user_by_username(session["username"])
    try:
        montant_brut = float(request.form.get("montant", "0").replace(",", "."))
        telephone = request.form.get("telephone").strip()

        if montant_brut <= 0:
            flash("Le montant doit être positif.", "error")
            return redirect(url_for("portefeuille"))

        if user["solde"] < montant_brut:
            flash("Solde insuffisant.", "error")
            return redirect(url_for("portefeuille"))

        # --- CALCUL DES FRAIS ---
        # On arrondit à 2 décimales
        config = get_config()
        montant_frais = round(montant_brut * config["frais_retrait"], 2)
        montant_net = montant_brut - montant_frais

        # 1. On débite le montant TOTAL (Brut) du solde de l'utilisateur
        success_debit, msg_debit = debit(user["username"], montant_brut)

        if success_debit:
            # 2. On enregistre la transaction avec les détails (Frais et Net)
            success_trans, msg_trans = create_transaction(
                user_id=user["id"],
                type_trans="retrait",
                montant_dec=montant_brut,  # Montant débité du compte
                telephone=telephone,
                frais_dec=montant_frais,  # <--- NOUVEAU
                net_dec=montant_net,  # <--- NOUVEAU
            )

            if success_trans:
                flash(
                    f"Retrait enregistré. Frais: {montant_frais} HTG. Vous recevrez : {montant_net} HTG.",
                    "success",
                )
            else:
                # Rollback si erreur DB
                credit(user["username"], montant_brut)
                flash("Erreur technique. Remboursé.", "error")
        else:
            flash(msg_debit, "error")

    except ValueError:
        flash("Montant invalide.", "error")

    return redirect(url_for("portefeuille"))


# === Route pour le Profil ===
@app.route("/profil")
@active_required
def profil():
    if "username" not in session:
        return redirect(url_for("login"))

    user = get_user_by_username(session["username"])
    return render_template("profil.html", user=user)
