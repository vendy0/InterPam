import os
import smtplib
from email.message import EmailMessage
from jinja2 import Template
import json
from pywebpush import webpush, WebPushException
import inspect
from markupsafe import Markup
from flask import url_for


def envoyer_email_generique(destinataire, sujet, contenu_html, contenu_texte):
    EMAIL_ADRESSE = os.getenv("EMAIL_ADRESSE")
    EMAIL_MOT_DE_PASSE = os.getenv("MAIL_PASSWORD")

    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = EMAIL_ADRESSE
    msg["To"] = destinataire

    msg.set_content(contenu_texte)
    msg.add_alternative(contenu_html, subtype="html")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_ADRESSE, EMAIL_MOT_DE_PASSE)
            smtp.send_message(msg)
        return True, "Succès"
    except Exception as e:
        return False, str(e)


def envoyer_invitation_admin(nom, email, lien):
    sujet = "Invitation Admin - InterPam"
    # 1. Charger le template depuis le fichier
    with open("templates/admin/emails/new_adm.html", "r", encoding="utf-8") as f:
        template_html = f.read()
    j2_template = Template(template_html)
    html = j2_template.render(nom=nom, lien=lien, url_for=url_for)
    corps_texte = f"Bonjour {nom}, Vous avez été invité sur la plateforme InterPam à devenir un administrateur. Voici le lien d'inscription : \n\n{lien}"
    return envoyer_email_generique(email, sujet, html, corps_texte)


def envoyer_mail_verification(nom, email, lien):
    """Envoie l'email de validation de compte (style InterPam)."""
    sujet = "Validez votre inscription - InterPam"

    # 1. Charger le nouveau template
    try:
        with open(
            "templates/admin/emails/verify_email.html", "r", encoding="utf-8"
        ) as f:
            template_html = f.read()
    except FileNotFoundError:
        # Fallback au cas où le dossier est différent
        with open("templates/verify_email.html", "r", encoding="utf-8") as f:
            template_html = f.read()

    j2_template = Template(template_html)

    # 2. Rendre le HTML
    html = j2_template.render(nom=nom, lien=lien)

    # 3. Version texte brut pour les vieux clients mail
    corps_texte = f"Bonjour {nom},\n\nMerci de vous être inscrit sur InterPam. Veuillez valider votre compte en cliquant sur ce lien : {lien}\n Note : Ce lien est valable pour 24h. \n\nL'équipe InterPam. "

    return envoyer_email_generique(email, sujet, html, corps_texte)


def welcome_email(nom, email, lien):
    sujet = "Bienvenue sur InterPam !"

    # 1. Charger le template depuis le fichier
    with open("templates/admin/emails/welcome.html", "r", encoding="utf-8") as f:
        template_html = f.read()

    # 2. Remplacer les variables
    j2_template = Template(template_html)
    html = j2_template.render(nom=nom, lien=lien, url_for=url_for)

    # 3. Version texte simple (pour les vieux clients mail)
    corps_texte = (
        f"Bonjour {nom}, bienvenue sur InterPam ! Accédez à votre espace ici : {lien}"
    )

    return envoyer_email_generique(email, sujet, html, corps_texte)


def password_reset_email(nom, email, lien):
    sujet = "Réinitialisation de mot de passe"

    # 1. Charger le template depuis le fichier
    with open("templates/_password_reset.html", "r", encoding="utf-8") as f:
        template_html = f.read()

    # 2. Remplacer les variables
    j2_template = Template(template_html)
    html = j2_template.render(nom=nom, lien=lien, url_for=url_for)

    # 3. Version texte simple (pour les vieux clients mail)
    corps_texte = f"Bonjour {nom}, Réinitialisez votre mot de passe ici : {lien}"

    return envoyer_email_generique(email, sujet, html, corps_texte)


def ban_notification(nom, email):
    sujet = "Compte suspendu"

    # 1. Charger le template depuis le fichier
    with open(
        "templates/admin/emails/ban_notification.html", "r", encoding="utf-8"
    ) as f:
        template_html = f.read()

    # 2. Remplacer les variables
    j2_template = Template(template_html)
    html = j2_template.render(nom=nom, url_for=url_for)

    # 3. Version texte simple (pour les vieux clients mail)
    corps_texte = f"Bonjour {nom}, Votre compte InterPam vient d'être suspendu !"

    return envoyer_email_generique(email, sujet, html, corps_texte)


def ret_notification(nom, email):
    sujet = "Compte restauré"

    # 1. Charger le template depuis le fichier
    with open(
        "templates/admin/emails/account_restored.html", "r", encoding="utf-8"
    ) as f:
        template_html = f.read()

    # 2. Remplacer les variables
    j2_template = Template(template_html)
    html = j2_template.render(nom=nom, url_for=url_for)

    # 3. Version texte simple (pour les vieux clients mail)
    corps_texte = f"Bonjour {nom}, Votre compte InterPam a été restauré. Vous pouvez désormais vous reconnecter !"

    return envoyer_email_generique(email, sujet, html, corps_texte)


def refus_notification(nom, email, message, lien=None, texte_bouton=None):
    sujet = "Mise à jour de transaction"

    # 1. Charger le template depuis le fichier
    with open(
        "templates/admin/emails/refusal_notification.html", "r", encoding="utf-8"
    ) as f:
        template_html = f.read()

    # 2. Remplacer les variables
    j2_template = Template(template_html)
    html = j2_template.render(nom=nom, url_for=url_for, message=message, titre=sujet)

    # 3. Version texte simple (pour les vieux clients mail)
    corps_texte = f"Votre demande a été examinée par notre service financier. Malheureusement, celle-ci a été refusée."

    return envoyer_email_generique(email, sujet, html, corps_texte)


def envoyer_notification_generale(nom, email, titre, message, lien=None, texte_bouton=None):
    """
    Envoie un email de notification flexible.
    'message' peut contenir du HTML simple.
    """
    sujet = f"InterPam - {titre}"

    # Lien par défaut si non fourni
    url_finale = lien if lien else url_for("home", _external=True)

    # 1. Charger et rendre le template HTML
    with open(
        "templates/admin/emails/general_notification.html", "r", encoding="utf-8"
    ) as f:
        template_html = f.read()

    j2_template = Template(template_html)
    html = j2_template.render(
        nom=nom,
        titre_entete=titre,
        message_principal=Markup(
            message
        ),  # Permet d'interpréter le HTML dans le template
        lien_action=url_finale,
        texte_bouton=texte_bouton if texte_bouton else "Accéder à InterPam",
    )

    # 2. Préparer la version texte brut (sans balises HTML)
    # On remplace les <br> par des retours à la ligne et on retire le reste
    message_clean = message.replace("<br>", "\n").replace("<br/>", "\n")
    import re

    message_clean = re.sub(
        "<[^<]+?>", "", message_clean
    )  # Supprime toutes les autres balises HTML

    corps_texte = inspect.cleandoc(f"""
        Bonjour {nom},

        {titre}

        {message_clean}

        Accédez ici : {url_finale}
    """)

    return envoyer_email_generique(email, sujet, html, corps_texte)


# 1. Récupération des variables d'environnement
PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
SUBJECT = os.getenv("VAPID_SUBJECT", "")
# 2. Configuration correcte pour l'envoi
VAPID_CLAIMS = {"sub": SUBJECT}
# Utilisation (exemple avec la clé privée)
VAPID_PRIVATE_KEY = PRIVATE_KEY


def envoyer_push_notification(subscription_json, title, message, url="/home"):
    """
    Envoie une notification à un utilisateur spécifique via son JSON d'abonnement.
    """
    try:
        # On transforme le string JSON de la BDD en dictionnaire
        subscription_info = json.loads(subscription_json)

        # Préparation du contenu de la notification (lu par sw.js)
        data = json.dumps({"title": title, "body": message, "url": url})

        webpush(
            subscription_info=subscription_info,
            data=data,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS,
        )
        return True, "Envoyé"
    except WebPushException as ex:
        print(f"Erreur WebPush: {ex}")
        # Si l'erreur est 410, l'utilisateur s'est désabonné, tu devrais supprimer l'abonnement en BDD
        return False, str(ex)
