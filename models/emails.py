# models/emails.py
import os
import smtplib
import json
import threading
import inspect
import re
from email.message import EmailMessage
from jinja2 import Template
from flask import url_for
from pywebpush import webpush, WebPushException
from markupsafe import Markup  # Indispensable pour injecter du HTML sûr

# --- CONFIGURATION ---
EMAIL_ADRESSE = os.getenv("EMAIL_ADRESSE")
EMAIL_MOT_DE_PASSE = os.getenv("MAIL_PASSWORD")

# Configuration WebPush
PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:admin@example.com")

VAPID_CLAIMS = {"sub": SUBJECT}
VAPID_PRIVATE_KEY = PRIVATE_KEY


# ==========================================
# 1. MOTEUR D'ENVOI EMAIL (ASYNC)
# ==========================================


def _thread_send_email(destinataire, sujet, contenu_html, contenu_texte):
    """
    Fonction exécutée en arrière-plan (Thread).
    """
    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = EMAIL_ADRESSE
    msg["To"] = destinataire

    # Définir le contenu texte brut (fallback)
    msg.set_content(contenu_texte)
    # Définir le contenu HTML
    msg.add_alternative(contenu_html, subtype="html")

    try:
        # Connexion SMTP sécurisée (SSL)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_ADRESSE, EMAIL_MOT_DE_PASSE)
            smtp.send_message(msg)

        # Log discret
        safe_email = (
            f"{destinataire[:3]}***{destinataire[destinataire.find('@') :]}"
            if "@" in destinataire
            else "***"
        )
        print(f"✅ Email envoyé (Thread) à : {safe_email}")

    except Exception as e:
        print(f"❌ Erreur envoi email (Thread) : {str(e)}")


def envoyer_email_generique(destinataire, sujet, contenu_html, contenu_texte):
    """
    Point d'entrée principal. Lance le thread et rend la main immédiatement.
    """
    if not EMAIL_ADRESSE or not EMAIL_MOT_DE_PASSE:
        print("⚠️ Configuration email manquante (env vars).")
        return False, "Configuration serveur incomplète."

    try:
        thread = threading.Thread(
            target=_thread_send_email,
            args=(destinataire, sujet, contenu_html, contenu_texte),
        )
        thread.start()
        return True, "Envoi lancé en arrière-plan"
    except Exception as e:
        return False, str(e)


# ==========================================
# 2. MOTEUR PUSH NOTIFICATION (ASYNC)
# ==========================================


def _thread_send_push(subscription_info, data):
    """
    Fonction exécutée en arrière-plan pour WebPush.
    """
    try:
        webpush(
            subscription_info=subscription_info,
            data=data,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS,
        )
        print("✅ Push envoyé (Thread)")
    except WebPushException as ex:
        # Erreur 410 = Gone (l'utilisateur s'est désabonné ou a nettoyé son cache)
        if ex.response and ex.response.status_code == 410:
            print("ℹ️ Push : Abonnement expiré ou invalide (410).")
        else:
            print(f"⚠️ Erreur Push WebPushException : {ex}")
    except Exception as e:
        print(f"❌ Erreur Push générique : {e}")


def envoyer_push_notification(subscription_json, title, message, url="/home"):
    """
    Parse le JSON d'abonnement et lance le thread d'envoi.
    """
    try:
        if not subscription_json:
            return False, "Pas d'abonnement pour cet utilisateur"

        if not VAPID_PRIVATE_KEY:
            return False, "Clé VAPID manquante sur le serveur"

        # Conversion du JSON stocké en base
        try:
            subscription_info = json.loads(subscription_json)
        except json.JSONDecodeError:
            return False, "Format d'abonnement invalide"

        # Payload pour le Service Worker
        data = json.dumps({"title": title, "body": message, "url": url})

        # Lancement du thread
        thread = threading.Thread(
            target=_thread_send_push, args=(subscription_info, data)
        )
        thread.start()

        return True, "Push lancé"
    except Exception as e:
        print(f"Erreur pré-envoi push : {e}")
        return False, str(e)


# ==========================================
# 3. TEMPLATES ET FONCTIONS SPÉCIFIQUES
# ==========================================


def _load_template(filename):
    """Helper pour charger un template avec gestion d'erreur basique."""
    paths = [
        f"templates/admin/emails/{filename}",
        f"templates/emails/{filename}",
        f"templates/{filename}",
    ]
    for path in paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    return None


def envoyer_invitation_admin(nom, email, lien):
    sujet = "Invitation Admin - InterPam"
    template_html = _load_template("new_adm.html")

    if template_html:
        html = Template(template_html).render(nom=nom, lien=lien)
    else:
        html = (
            f"<p>Bonjour {nom}, <br>Devenez Admin ici : <a href='{lien}'>{lien}</a></p>"
        )

    corps_texte = (
        f"Bonjour {nom}, bienvenue dans l'équipe. Activez votre compte : {lien}"
    )
    return envoyer_email_generique(email, sujet, html, corps_texte)


def envoyer_notification_email(
    nom, email, titre, message, url_action, texte_bouton="Voir détails"
):
    sujet = f"Notification - {titre}"
    template_html = _load_template("notif.html")

    if template_html:
        html = Template(template_html).render(
            titre=titre, message=message, url=url_action, bouton=texte_bouton
        )
    else:
        html = (
            f"<h1>{titre}</h1><p>{message}</p><a href='{url_action}'>{texte_bouton}</a>"
        )

    # Nettoyage HTML pour le texte brut
    message_clean = re.sub("<[^<]+?>", "", message)
    corps_texte = inspect.cleandoc(f"""
        Bonjour {nom},
        {titre}
        {message_clean}
        Lien : {url_action}
    """)

    return envoyer_email_generique(email, sujet, html, corps_texte)


def envoyer_mail_verification(nom, email, lien):
    sujet = "Validez votre inscription - InterPam"
    template_html = _load_template("verify_email.html")

    if template_html:
        html = Template(template_html).render(nom=nom, lien=lien)
    else:
        html = (
            f"<p>Bonjour {nom}, merci de valider : <a href='{lien}'>Cliquez ici</a></p>"
        )

    corps_texte = f"Bonjour {nom},\nValidez votre compte : {lien}\n(Valable 24h)"
    return envoyer_email_generique(email, sujet, html, corps_texte)


def welcome_email(nom, email, lien):
    sujet = "Bienvenue sur InterPam !"
    template_html = _load_template("welcome.html")

    if template_html:
        html = Template(template_html).render(nom=nom, lien=lien, url_for=url_for)
    else:
        html = f"<h1>Bienvenue {nom} !</h1><p>Accédez à votre espace : <a href='{lien}'>Connexion</a></p>"

    corps_texte = (
        f"Bonjour {nom}, bienvenue sur InterPam ! Accédez à votre espace ici : {lien}"
    )
    return envoyer_email_generique(email, sujet, html, corps_texte)


def password_reset_email(nom, email, lien):
    sujet = "Réinitialisation de mot de passe"
    # Note: souvent ce template est à la racine ou dans un dossier spécifique
    template_html = _load_template("_password_reset.html")

    if template_html:
        html = Template(template_html).render(nom=nom, lien=lien, url_for=url_for)
    else:
        html = f"<p>Bonjour {nom}, réinitialisez votre mot de passe : <a href='{lien}'>Cliquez ici</a></p>"

    corps_texte = f"Bonjour {nom}, réinitialisez votre mot de passe ici : {lien}"
    return envoyer_email_generique(email, sujet, html, corps_texte)


def ban_notification(nom, email):
    sujet = "Compte suspendu"
    template_html = _load_template("ban_notification.html")

    if template_html:
        html = Template(template_html).render(nom=nom, url_for=url_for)
    else:
        html = f"<p>Bonjour {nom}, votre compte a été suspendu.</p>"

    corps_texte = f"Bonjour {nom}, Votre compte InterPam vient d'être suspendu !"
    return envoyer_email_generique(email, sujet, html, corps_texte)


def ret_notification(nom, email):
    sujet = "Compte restauré"
    template_html = _load_template("account_restored.html")

    if template_html:
        html = Template(template_html).render(nom=nom, url_for=url_for)
    else:
        html = f"<p>Bonjour {nom}, votre compte est rétabli.</p>"

    corps_texte = f"Bonjour {nom}, Votre compte InterPam a été restauré."
    return envoyer_email_generique(email, sujet, html, corps_texte)


def refus_notification(nom, email, message, lien=None, texte_bouton=None):
    sujet = "Mise à jour de transaction"
    template_html = _load_template("refusal_notification.html")

    if template_html:
        html = Template(template_html).render(
            nom=nom, url_for=url_for, message=message, titre=sujet
        )
    else:
        html = f"<h3>Refus de transaction</h3><p>{message}</p>"

    corps_texte = "Votre demande a été examinée et refusée par notre service financier."
    return envoyer_email_generique(email, sujet, html, corps_texte)


def envoyer_notification_generale(
    nom, email, titre, message, lien=None, texte_bouton=None
):
    """
    Envoie un email flexible. Le message peut contenir du HTML.
    """
    sujet = f"InterPam - {titre}"
    url_finale = lien if lien else url_for("home", _external=True)

    template_html = _load_template("general_notification.html")

    if template_html:
        html = Template(template_html).render(
            nom=nom,
            titre_entete=titre,
            message_principal=Markup(
                message
            ),  # Utilisation de Markup pour valider le HTML
            lien_action=url_finale,
            texte_bouton=texte_bouton if texte_bouton else "Accéder à InterPam",
        )
    else:
        html = (
            f"<h2>{titre}</h2><div>{message}</div><br><a href='{url_finale}'>Voir</a>"
        )

    # Nettoyage pour le format texte
    message_clean = message.replace("<br>", "\n").replace("<br/>", "\n")
    message_clean = re.sub("<[^<]+?>", "", message_clean)

    corps_texte = inspect.cleandoc(f"""
        Bonjour {nom},

        {titre}

        {message_clean}

        Accédez ici : {url_finale}
    """)

    return envoyer_email_generique(email, sujet, html, corps_texte)
