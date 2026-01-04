import pytest
import sqlite3
from unittest.mock import patch
from models.bet import placer_pari, get_fiches_detaillees

@pytest.fixture
def mock_db_paris():
    """Crée une base avec les tables parieurs, paris, matchs et options."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # On recrée la structure simplifiée nécessaire
    conn.executescript("""
        CREATE TABLE parieurs (id INTEGER PRIMARY KEY, solde INTEGER, username TEXT);
        CREATE TABLE matchs (id INTEGER PRIMARY KEY, equipe_a TEXT, equipe_b TEXT);
        CREATE TABLE options (id INTEGER PRIMARY KEY, match_id INTEGER, libelle TEXT, cote REAL, winner TEXT, categorie TEXT);
        CREATE TABLE paris (id INTEGER PRIMARY KEY AUTOINCREMENT, mise INTEGER, gain_potentiel INTEGER, date_pari TEXT, parieur_id INTEGER, statut TEXT DEFAULT 'en_attente');
        CREATE TABLE matchs_paris (paris_id INTEGER, matchs_id INTEGER, option_id INTEGER);
        
        -- Insertion d'un utilisateur de test avec 1000 centimes (10 HTG)
        INSERT INTO parieurs (id, solde, username) VALUES (1, 1000, 'testeur');
        -- Insertion d'un match et d'une option
        INSERT INTO matchs (id, equipe_a, equipe_b) VALUES (10, 'Real', 'Barca');
        INSERT INTO options (id, match_id, libelle, cote) VALUES (100, 10, 'Victoire Real', 2.0);
    """)
    
    with patch('models.bet.get_db_connection') as mocked_get_conn:
        mocked_get_conn.return_value.__enter__.return_value = conn
        yield conn
    conn.close()

def test_placer_pari_succes(mock_db_paris):
    # On parie 5 HTG (500 centimes) pour gagner 10 HTG
    success, msg = placer_pari(parieur_id=1, match_id=10, mise_dec=5, gain_dec=10, date_pari="2026-01-04", options_ids=[100])
    
    assert success is True
    # Vérification du débit : 1000 - 500 = 500
    res = mock_db_paris.execute("SELECT solde FROM parieurs WHERE id = 1").fetchone()
    assert res["solde"] == 500
    
    # Vérification de la création du pari
    pari = mock_db_paris.execute("SELECT * FROM paris WHERE parieur_id = 1").fetchone()
    assert pari["mise"] == 500

def test_placer_pari_solde_insuffisant(mock_db_paris):
    # On essaie de parier 100 HTG alors qu'on n'a que 10 HTG
    success, msg = placer_pari(parieur_id=1, match_id=10, mise_dec=100, gain_dec=200, date_pari="now", options_ids=[100])
    
    assert success is False
    assert msg == "Solde insuffisant"
    # Le solde ne doit pas avoir bougé
    res = mock_db_paris.execute("SELECT solde FROM parieurs WHERE id = 1").fetchone()
    assert res["solde"] == 1000
