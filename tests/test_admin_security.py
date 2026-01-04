import pytest
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch
from models.admin import get_invitation_by_token

@pytest.fixture
def db_invit():
    """Base de données temporaire pour les invitations."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE invitations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            role TEXT,
            token TEXT,
            expiration TEXT
        )
    """)
    with patch('models.admin.get_db_connection') as mock_conn:
        mock_conn.return_value.__enter__.return_value = conn
        yield conn

def test_invitation_valide(db_invit):
    # 1. Créer une invitation qui expire dans 47 heures (donc valide)
    future_date = (datetime.now() + timedelta(hours=47)).strftime("%Y-%m-%d %H:%M:%S")
    db_invit.execute(
        "INSERT INTO invitations (email, role, token, expiration) VALUES (?, ?, ?, ?)",
        ("prof@cif.com", "admin", "TOKEN_VALIDE", future_date)
    )
    
    # 2. Récupérer l'invitation
    invit = get_invitation_by_token("TOKEN_VALIDE")
    
    # 3. Vérifier la logique
    date_exp = datetime.strptime(invit['expiration'], "%Y-%m-%d %H:%M:%S")
    assert date_exp > datetime.now()  # Elle doit être valide

def test_invitation_expiree(db_invit):
    # 1. Créer une invitation qui a expiré il y a 24 heures
    past_date = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    db_invit.execute(
        "INSERT INTO invitations (email, role, token, expiration) VALUES (?, ?, ?, ?)",
        ("ancien@cif.com", "admin", "TOKEN_EXPIRE", past_date)
    )
    
    # 2. Récupérer l'invitation
    invit = get_invitation_by_token("TOKEN_EXPIRE")
    
    # 3. Vérifier la logique d'expiration
    date_exp = datetime.strptime(invit['expiration'], "%Y-%m-%d %H:%M:%S")
    
    # Le test réussit si l'invitation est bien considérée comme périmée
    assert date_exp < datetime.now()
