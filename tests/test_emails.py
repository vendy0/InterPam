import pytest
from unittest.mock import patch, MagicMock, mock_open
from models.emails import envoyer_invitation_admin, envoyer_push_notification

# --- TEST DES EMAILS ---

def test_envoyer_invitation_admin():
    # 1. On simule le contenu du fichier HTML pour ne pas dépendre du disque
    fake_template = "<html><body>Bonjour {{nom}}, voici ton {{lien}}</body></html>"
    
    # On mocke : 1. l'ouverture de fichier, 2. le serveur SMTP, 3. url_for de Flask
    with patch("builtins.open", mock_open(read_data=fake_template)), \
         patch("smtplib.SMTP_SSL") as mock_smtp, \
         patch("models.emails.url_for", return_value="http://localhost/setup"):
        
        # Configuration du faux serveur SMTP
        instance = mock_smtp.return_value.__enter__.return_value
        
        # Appel de la fonction
        success, msg = envoyer_invitation_admin("Junior", "test@cif.com", "http://lien.com")
        
        # VERIFICATIONS
        assert success is True
        # On vérifie que login() a bien été appelé avec les variables d'environnement
        assert instance.login.called
        # On vérifie qu'un message a bien été envoyé
        assert instance.send_message.called

# --- TEST DES NOTIFICATIONS PUSH ---

def test_envoyer_push_notification_logic():
    # Un faux abonnement au format JSON comme stocké dans ta BDD
    fake_sub = '{"endpoint": "https://fcm.googleapis.com/...", "keys": {"p256dh": "...", "auth": "..."}}'
    
    # On mocke la fonction webpush pour ne pas envoyer de vraie requête internet
    with patch("models.emails.webpush") as mock_webpush:
        success, msg = envoyer_push_notification(fake_sub, "Titre", "Message test")
        
        assert success is True
        # On vérifie que webpush a été appelé avec les bonnes infos
        assert mock_webpush.called
        # On vérifie que le JSON a bien été parsé
        args, kwargs = mock_webpush.call_args
        assert kwargs['subscription_info']['endpoint'] == "https://fcm.googleapis.com/..."

