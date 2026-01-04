# tests/test_auth_validation.py
import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_register_validation_errors(client):
    # Test 1 : Nom avec des caractères interdits (ex: chiffres)
    response = client.post(
        "/traitement-register",
        data={
            "first_name": "Jean123",
            "last_name": "Dupont",
            "username": "jdupont",
            "email": "j@cif.com",
            "age": "18",
            "classe": "Philo",
            "mdp": "password123",
            "mdpConfirm": "password123",
            "rules": "on",
        },
        follow_redirects=True,
    )
    assert (
        b"Le nom et le pr\xc3\xa9nom ne doivent contenir que des lettres"
        in response.data
    )

    # Test 2 : Username avec caractères spéciaux interdits (@, !, etc.)
    response = client.post(
        "/traitement-register",
        data={
            "first_name": "Jean",
            "last_name": "Dupont",
            "username": "jean@admin",
            "email": "j@cif.com",
            "age": "18",
            "classe": "Philo",
            "mdp": "password123",
            "mdpConfirm": "password123",
            "rules": "on",
        },
        follow_redirects=True,
    )
    assert (
        b"Le nom d'utilisateur ne peut contenir que des lettres, chiffres"
        in response.data
    )

# tests/test_ticket_security.py
from unittest.mock import patch

def test_valider_ticket_match_ferme(client):
    # 1. On simule un ticket dans la session
    with client.session_transaction() as sess:
        sess['username'] = 'testuser'
        sess['ticket'] = {'1': 100} # Match 1, Option 100

    # 2. On simule que 'verifier_matchs_ouverts' renvoie False (le match vient de fermer)
    with patch('app.get_user_by_username'), \
         patch('app.verifier_matchs_ouverts', return_value=False):
        
        response = client.post('/valider_ticket', data={"mise": "50"}, follow_redirects=True)
        
        # On vérifie que l'utilisateur est bloqué avec le message d'erreur
        assert b"Certains matchs de votre ticket ne sont plus disponibles" in response.data
