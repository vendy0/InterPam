from database.setup import initialiser_bdd, DB_NAME
import os


def test_initialisation_tables():
    # On utilise un nom de fichier temporaire pour le test
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


import pytest
import sqlite3
from unittest.mock import patch, MagicMock

# On importe les fonctions depuis ton fichier models/match.py
from models.match import (
    ajouter_match,
    get_programmes,
    get_matchs_actifs,
    get_historique_matchs,
    verifier_matchs_ouverts,
)


# --- LA FIXTURE (Configuration de la base temporaire) ---
@pytest.fixture
def mock_db():
    # Crée une base totalement vide en mémoire RAM (disparaît après le test)
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # On crée les tables minimales pour que tes fonctions ne plantent pas
    conn.execute("""
        CREATE TABLE matchs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipe_a TEXT,
            equipe_b TEXT,
            date_match TEXT,
            statut TEXT,
            type_match TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER,
            libelle TEXT,
            cote REAL,
            categorie TEXT
        )
    """)
    conn.execute("CREATE TABLE parieurs (push_subscription TEXT)")

    # /!\ CRUCIAL : On patch get_db_connection LÀ OÙ IL EST UTILISÉ (models.match)
    with patch("models.match.get_db_connection") as mocked_get_conn:
        mocked_get_conn.return_value.__enter__.return_value = conn
        yield conn
    conn.close()


# --- LE TEST ---
def test_complet_gestion_matchs(mock_db):
    # 1. On teste l'ajout (ID devrait être 1 car la base est vide)
    with patch("models.match.envoyer_push_notification"):
        m_id = ajouter_match("Real", "Barca", "2026-05-01", "foot")

    # Si le patch fonctionne, m_id sera forcément 1
    assert m_id == 1

    # 2. Vérifier qu'il est bien considéré comme actif
    actifs = get_matchs_actifs()
    assert len(actifs) == 1
    assert actifs[1]["equipe_a"] == "Real"

    # 3. Tester la structure complexe de get_programmes
    mock_db.execute(
        "INSERT INTO options (match_id, libelle, cote, categorie) VALUES (1, 'Real Gagne', 1.5, '1X2')"
    )
    programme = get_programmes()
    assert 1 in programme
    assert programme[1]["options"][0]["libelle"] == "Real Gagne"

    # 4. Tester la vérification des matchs ouverts
    # L'option ID insérée juste au dessus est 1
    assert verifier_matchs_ouverts([1]) is True
