import pytest
import sqlite3
import os
from unittest.mock import patch, MagicMock

# Imports des fonctions à tester
from database.setup import initialiser_bdd
from models.match import (
    get_programmes,
    get_matchs_actifs,
    get_historique_matchs,
    verifier_matchs_ouverts,
)
from models.admin import ajouter_match

# --- 1. TESTS D'INITIALISATION ---

def test_initialisation_tables():
    """Vérifie que le schéma de la base de données se crée correctement."""
    test_db = "test_init.db"
    with patch("database.setup.DB_NAME", test_db):
        initialiser_bdd()

        conn = sqlite3.connect(test_db)
        cur = conn.cursor()
        # Vérifier si la table parieurs existe
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='parieurs'"
        )
        assert cur.fetchone() is not None
        conn.close()
        
        if os.path.exists(test_db):
            os.remove(test_db)

# --- 2. LA FIXTURE (Cruciale pour isoler les tests) ---

@pytest.fixture
def mock_db():
    """Crée une base en mémoire et patche les accès DB des modèles."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Création du schéma minimal requis
    conn.execute("""
        CREATE TABLE matchs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipe_a TEXT,
            equipe_b TEXT,
            date_match TEXT,
            statut TEXT DEFAULT 'ouvert',
            type_match TEXT DEFAULT 'foot'
        )
    """)
    conn.execute("""
        CREATE TABLE options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER,
            libelle TEXT,
            cote REAL,
            categorie TEXT,
            winner INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE TABLE parieurs (id INTEGER PRIMARY KEY, push_subscription TEXT)")

    # On patche get_db_connection dans TOUS les modules qui l'utilisent
    with patch("models.match.get_db_connection") as mock_m, \
         patch("models.admin.get_db_connection") as mock_a:
        
        # On définit le comportement du context manager (with get_db_connection():)
        mock_m.return_value.__enter__.return_value = conn
        mock_a.return_value.__enter__.return_value = conn
        
        yield conn
    
    conn.close()

# --- 3. LE TEST DE LOGIQUE ---

def test_complet_gestion_matchs(mock_db):
    """Test le cycle de vie d'un match : création, statut et options."""
    
    # 1. On teste l'ajout (doit être ID 1 car mock_db est fraîche)
    # On patche la notification pour éviter les erreurs SMTP/Push
    with patch("models.admin.envoyer_push_notification"):
        m_id = ajouter_match("Real", "Barca", "2026-05-01", "foot")

    assert m_id == 1

    # 2. Vérifier qu'il est bien considéré comme actif
    # get_matchs_actifs() filtre généralement sur statut = 'ouvert'
    actifs = get_matchs_actifs()
    assert len(actifs) == 1
    assert actifs[1]["equipe_a"] == "Real"

    # 3. Tester la structure de get_programmes
    # On insère manuellement une option dans la base mockée
    mock_db.execute(
        "INSERT INTO options (match_id, libelle, cote, categorie) VALUES (1, 'Real Gagne', 1.5, '1X2')"
    )
    mock_db.commit()

    programme = get_programmes()
    assert 1 in programme
    assert programme[1]["options"][0]["libelle"] == "Real Gagne"

    # 4. Tester la vérification des matchs ouverts
    # L'option insérée a l'ID 1
    assert verifier_matchs_ouverts([1]) is True
