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


# welcome_email("Andy", "andyvenson99@gmail.com", "Td")
