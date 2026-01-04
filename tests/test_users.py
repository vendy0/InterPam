import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from models.user import (
    ajouter_parieur, get_user_by_username, credit, debit, 
    get_users, save_recuperation
)

@pytest.fixture
def mock_db_user():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Création de la table parieurs avec la colonne solde par défaut à 0
    conn.execute("""
        CREATE TABLE parieurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prenom TEXT, nom TEXT, username TEXT, email TEXT, 
            age INTEGER, classe TEXT, mdp TEXT, role TEXT, 
            created_at TEXT, solde INTEGER DEFAULT 0, actif INTEGER DEFAULT 1,
            push_subscription TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE recuperations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT, token TEXT, expiration TEXT
        )
    """)
    
    # On patch l'accès à la DB pour TOUTES les fonctions du module user
    with patch('models.user.get_db_connection') as mocked_get_conn:
        mocked_get_conn.return_value.__enter__.return_value = conn
        yield conn
    conn.close()

# --- LES TESTS ---

def test_gestion_financiere(mock_db_user):
    # 1. Créer un utilisateur
    user_data = {
        "prenom": "Jean", "nom": "Dupont", "username": "jdupont",
        "email": "jean@cif.com", "age": 17, "classe": "Rhéto",
        "mdp": "secret", "created_at": "2026-01-04", "role": "parieur"
    }
    ajouter_parieur(user_data)

    # 2. Tester le CREDIT (100 HTG)
    # On simule la notif push pour éviter les erreurs de bibliothèque
    with patch('models.user.envoyer_push_notification'):
        success, msg = credit("jdupont", 100)
        assert success is True
    
    user = get_user_by_username("jdupont")
    assert user["solde"] == 100.0  # Vérifie la conversion depuis_centimes

    # 3. Tester le DEBIT (40 HTG)
    with patch('models.user.envoyer_push_notification'):
        success, msg = debit("jdupont", 40)
        assert success is True
    
    user = get_user_by_username("jdupont")
    assert user["solde"] == 60.0

    # 4. Tester le débit excessif (Solde insuffisant)
    success, msg = debit("jdupont", 1000)
    assert success is False
    assert msg == "Solde insuffisant !"

def test_recherche_et_filtres(mock_db_user):
    # Ajouter deux utilisateurs pour le test
    ajouter_parieur({"prenom": "Alice", "nom": "A", "username": "alice", "email": "a@a.com", "age": 18, "classe": "Philo", "mdp": "1", "created_at": "now"})
    ajouter_parieur({"prenom": "Bob", "nom": "B", "username": "bob", "email": "b@b.com", "age": 19, "classe": "Philo", "mdp": "2", "created_at": "now"})

    # Tester get_users sans filtre
    tous = get_users()
    assert len(tous) == 2

    # Tester le filtre par email
    from models.user import get_user_by_email
    user = get_user_by_email("a@a.com")
    assert user["username"] == "alice"

def test_recuperation_password(mock_db_user):
    # Tester la sauvegarde du token de récup
    success = save_recuperation("test@cif.com", "TOKEN123", "2026-01-06")
    assert success is True
    
    # Vérifier en base
    res = mock_db_user.execute("SELECT * FROM recuperations WHERE token = 'TOKEN123'").fetchone()
    assert res["email"] == "test@cif.com"
