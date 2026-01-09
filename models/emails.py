import os
import smtplib
from email.message import EmailMessage
from jinja2 import Template
import json
from pywebpush import webpush, WebPushException
import inspect
from flask import url_for
import threading  # <--- Le module magique

# --- CONFIGURATION (inchangée) ---
EMAIL_ADRESSE = os.getenv("EMAIL_ADRESSE")
EMAIL_MOT_DE_PASSE = os.getenv("MAIL_PASSWORD")
PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
SUBJECT = os.getenv("VAPID_SUBJECT", "")
VAPID_CLAIMS = {"sub": SUBJECT}
VAPID_PRIVATE_KEY = PRIVATE_KEY

# ==========================================
# 1. GESTION DES EMAILS (ASYNC)
# ==========================================

def _thread_send_email(destinataire, sujet, contenu_html, contenu_texte):
    """
    Cette fonction s'exécute en arrière-plan.
    Elle prend le temps qu'il faut, l'admin ne l'attend pas.
    """
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
        print(f"✅ Email envoyé à {destinataire} (Background)")
    except Exception as e:
        # Comme on est en background, on ne peut pas 'return False' à l'utilisateur.
        # On affiche juste l'erreur dans la console du serveur.
        print(f"❌ Erreur envoi email background : {str(e)}")

def envoyer_email_generique(destinataire, sujet, contenu_html, contenu_texte):
    """
    Fonction principale appelée par tes routes.
    Elle lance le thread et répond tout de suite "Succès".
    """
    try:
        # On crée un processus parallèle pour envoyer l'email
        thread = threading.Thread(
            target=_thread_send_email, 
            args=(destinataire, sujet, contenu_html, contenu_texte)
        )
        thread.start()
        
        # On retourne Vrai immédiatement, sans attendre Gmail
        return True, "Envoi lancé en arrière-plan"
    except Exception as e:
        return False, str(e)


def envoyer_invitation_admin(nom, email, lien):
    # Cette fonction prépare le contenu, c'est très rapide, pas besoin de thread ici.
    # Le thread se lancera dans 'envoyer_email_generique'.
    sujet = "Invitation Admin - InterPam"
    try:
        with open("templates/admin/emails/new_adm.html", "r", encoding="utf-8") as f:
            template_html = f.read()
        j2_template = Template(template_html)
        html = j2_template.render(nom=nom, lien=lien)
    except Exception:
        html = f"Bonjour {nom}, voici votre lien : {lien}"

    corps_texte = f"Bonjour {nom}, bienvenue admin. Lien: {lien}"
    
    return envoyer_email_generique(email, sujet, html, corps_texte)


def envoyer_notification_email(nom, email, titre, message, url_action, texte_bouton="Voir détails"):
    # Pareil, préparation rapide -> envoi lent en background
    sujet = f"Notification - {titre}"
    
    try:
        with open("templates/admin/emails/notif.html", "r", encoding="utf-8") as f:
            template_html = f.read()
        
        j2_template = Template(template_html)
        html = j2_template.render(
            titre=titre,
            message=message,
            url=url_action,
            bouton=texte_bouton
        )
    except Exception:
        html = f"<h1>{titre}</h1><p>{message}</p><a href='{url_action}'>{texte_bouton}</a>"

    import re
    message_clean = re.sub("<[^<]+?>", "", message) # Nettoyage HTML simple

    corps_texte = inspect.cleandoc(f"""
        Bonjour {nom},
        {titre}
        {message_clean}
        Accédez ici : {url_action}
    """)

    return envoyer_email_generique(email, sujet, html, corps_texte)


# ==========================================
# 2. GESTION DES PUSH (ASYNC)
# ==========================================

def _thread_send_push(subscription_info, data):
    """
    Fonction lourde exécutée en background pour le Push.
    """
    try:
        webpush(
            subscription_info=subscription_info,
            data=data,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS,
        )
        print("✅ Push envoyé (Background)")
    except WebPushException as ex:
        # Souvent les erreurs ici sont dues à des utilisateurs qui ont révoqué la permission
        print(f"⚠️ Erreur Push (peut-être expiré) : {ex}")
    except Exception as e:
        print(f"❌ Erreur Push critique : {e}")

def envoyer_push_notification(subscription_json, title, message, url="/home"):
    """
    Lance le push en arrière-plan.
    """
    try:
        if not subscription_json:
            return False, "Pas d'abonnement"

        subscription_info = json.loads(subscription_json)
        data = json.dumps({"title": title, "body": message, "url": url})

        # Lancement du thread
        thread = threading.Thread(
            target=_thread_send_push,
            args=(subscription_info, data)
        )
        thread.start()

        return True, "Push lancé"
    except Exception as e:
        print(f"Erreur pré-envoi push : {e}")
        return False, str(e)
