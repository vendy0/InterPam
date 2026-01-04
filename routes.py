import os
import json
import secrets
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

from admin_routes import admin_bp, users_bp, matchs_bp
from models.match import *
from models.user import *
from models.bet import *
from models.emails import *

load_dotenv()

app = Flask(__name__)
app.register_blueprint(admin_bp)
app.register_blueprint(users_bp)
app.register_blueprint(matchs_bp)

# ================= CONFIG =================
app.config["SECRET_KEY_SESSION"] = os.getenv("SECRET_KEY_SESSION")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["DB_PATH"] = os.getenv("DB_PATH")
app.config["EMAIL_ADRESSE"] = os.getenv("EMAIL_ADRESSE")
app.config["VAPID_PRIVATE_KEY"] = os.getenv("VAPID_PRIVATE_KEY")
app.config["VAPID_SUBJECT"] = os.getenv("VAPID_SUBJECT")

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

app.secret_key = os.getenv("SECRET_KEY_SESSION")

# ================= UTILS =================
def clean_input(val):
    return val.strip() if val and isinstance(val, str) else ""

def set_date(date_a_tester):
    try:
        partie_date, partie_heure = date_a_tester.split(" ")
        heure_formatee = partie_heure[:5]
    except ValueError:
        return date_a_tester

    today = date.today()
    if partie_date == today.isoformat():
        return f"Aujourd'hui à {heure_formatee}"
    if partie_date == (today - timedelta(days=1)).isoformat():
        return f"Hier à {heure_formatee}"
    if partie_date == (today + timedelta(days=1)).isoformat():
        return f"Demain à {heure_formatee}"
    return f"{partie_date} à {heure_formatee}"

def valider_nom_prenom(entree):
    pattern = r"^[a-zA-ZàâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ\s'.-]+$"
    return bool(re_match(pattern, entree))

# ================= CONTEXT =================
@app.context_processor
def inject_user():
    user = get_user_by_username(session["username"]) if "username" in session else None
    return dict(current_user=user)

app.jinja_env.globals.update(set_date=set_date)

@app.template_filter("devise")
def format_devise(valeur_centimes):
    return "{:,.2f} HTG".format(valeur_centimes / 100)

# ================= AUTH =================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login():
    return redirect(url_for("home")) if "username" in session else render_template("auth.html")

@app.route("/register")
def register():
    return redirect(url_for("home")) if "username" in session else render_template("auth.html", register=True)

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/traitement-login", methods=["POST", "GET"])
def traitementLogin():
    if request.method == "GET":
        return render_template("auth.html")

    email_username = clean_input(request.form.get("email_username"))
    mdp = request.form.get("mdp")
    remember = bool(request.form.get("remember"))

    if not email_username or not mdp:
        return render_template("auth.html", loginError="Tous les champs doivent être remplis !")

    user = get_user_by_email(email_username) or get_user_by_username(email_username)
    if not user or not check_password_hash(user["mdp"], mdp):
        return render_template("auth.html", loginError="Identifiants incorrects")

    if not user["actif"]:
        return render_template("auth.html", loginError="Compte suspendu")

    session.clear()
    session["username"] = user["username"]
    session.permanent = remember
    return redirect(url_for("home"))

# ================= REGISTER =================
@app.route("/traitement-register", methods=["POST"])
def traitementRegister():
    data = request.form
    prenom = clean_input(data.get("first_name"))
    nom = clean_input(data.get("last_name"))
    username = clean_input(data.get("username"))
    email = clean_input(data.get("email"))
    age = data.get("age")
    classe = clean_input(data.get("classe"))
    mdp = data.get("mdp")
    mdpConfirm = data.get("mdpConfirm")
    rules = data.get("rules")

    if not all([prenom, nom, username, email, age, classe, mdp, mdpConfirm]):
        return render_template("auth.html", error="Tous les champs sont obligatoires")

    if not valider_nom_prenom(prenom) or not valider_nom_prenom(nom):
        return render_template("auth.html", error="Nom ou prénom invalide")

    if not re_match(r"^[a-zA-Z0-9_]+$", username):
        return render_template("auth.html", error="Nom d'utilisateur invalide")

    if mdp != mdpConfirm or len(mdp) < 8:
        return render_template("auth.html", error="Mot de passe invalide")

    if get_user_by_email(email) or get_user_by_username(username):
        return render_template("auth.html", error="Utilisateur déjà existant")

    if not rules:
        return render_template("auth.html", error="Vous devez accepter les règles")

    user = {
        "prenom": prenom,
        "nom": nom,
        "username": username,
        "email": email,
        "age": int(age),
        "classe": classe,
        "mdp": generate_password_hash(mdp),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    ajouter_parieur(user)
    flash("Compte créé avec succès", "success")
    welcome_email(prenom, email, url_for("home", _external=True))

    session["username"] = username
    session.permanent = False
    return redirect(url_for("home"))