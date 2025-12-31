import smtplib
from email.message import EmailMessage
from jinja2 import Template


def envoyer_email_generique(destinataire, sujet, contenu_html, contenu_texte):
    # Configuration (À mettre en variables d'environnement idéalement)
    EMAIL_ADRESSE = "interpam.school@gmail.com"
    EMAIL_MOT_DE_PASSE = "inqlvpgskrkezcha"

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
    html = j2_template.render(nom=nom, lien=lien)
    corps_texte = f"Bonjour {nom}, Vous avez été invité sur la plateforme InterPam à devenir un administrateur. Voici le lien d'inscription : \n\n{lien}"
    return envoyer_email_generique(email, sujet, html, corps_texte)


def welcome_email(nom, email, lien):
    sujet = "Bienvenue sur InterPam !"

    # 1. Charger le template depuis le fichier
    with open("templates/admin/emails/welcome.html", "r", encoding="utf-8") as f:
        template_html = f.read()

    # 2. Remplacer les variables
    j2_template = Template(template_html)
    html = j2_template.render(nom=nom, lien=lien)

    # 3. Version texte simple (pour les vieux clients mail)
    corps_texte = (
        f"Bonjour {nom}, bienvenue sur InterPam ! Accédez à votre espace ici : {lien}"
    )

    return envoyer_email_generique(email, sujet, html, corps_texte)


import inspect
from markupsafe import Markup
from jinja2 import Template
from flask import url_for


def envoyer_notification_generale(
    nom, email, titre, message, lien=None, texte_bouton=None
):
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
        texte_bouton=texte_bouton or "Accéder à InterPam",
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
