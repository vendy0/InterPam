import pytest
import sqlite3
from unittest.mock import patch, MagicMock
from models.admin import executer_settlement_match, valider_option_gagnante

# On crée une classe qui enveloppe la connexion pour ignorer l'appel à close()
class ConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn
    def __getattr__(self, name):
        return getattr(self.conn, name)
    def close(self):
        # On ne fait rien ici pour garder la base en mémoire vivante
        pass

@pytest.fixture
def db_settle():
    """Base de données avec un parieur, un match et un pari combiné."""
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    
    # On utilise notre Wrapper au lieu de la connexion brute
    conn = ConnectionWrapper(raw_conn)

    conn.executescript("""
        CREATE TABLE parieurs (id INTEGER PRIMARY KEY, solde INTEGER, push_subscription TEXT);
        CREATE TABLE matchs (id INTEGER PRIMARY KEY, equipe_a TEXT, equipe_b TEXT, statut TEXT);
        CREATE TABLE options (id INTEGER PRIMARY KEY, match_id INTEGER, winner INTEGER, categorie TEXT);
        CREATE TABLE paris (id INTEGER PRIMARY KEY, parieur_id INTEGER, gain_potentiel INTEGER, statut TEXT);
        CREATE TABLE matchs_paris (paris_id INTEGER, matchs_id INTEGER, option_id INTEGER);

        INSERT INTO parieurs (id, solde) VALUES (1, 1000); 
        INSERT INTO matchs (id, equipe_a, equipe_b, statut) VALUES (10, 'Haiti', 'Cuba', 'ouvert');
        INSERT INTO options (id, match_id, categorie) VALUES (100, 10, '1X2');
        
        INSERT INTO paris (id, parieur_id, gain_potentiel, statut) VALUES (50, 1, 1500, 'En attente');
        INSERT INTO matchs_paris (paris_id, matchs_id, option_id) VALUES (50, 10, 100);
    """)
    
    with patch('sqlite3.connect', return_value=conn):
        yield conn
    raw_conn.close() # On ferme réellement à la fin du test

def test_pari_gagnant_et_paiement(db_settle):
    with patch('models.admin.get_db_connection') as mock_conn:
        mock_conn.return_value.__enter__.return_value = db_settle
        valider_option_gagnante(100, 10)

    with patch('models.admin.envoi_notification_gain'):
        success, msg = executer_settlement_match(10)
    
    assert success is True
    res = db_settle.execute("SELECT solde FROM parieurs WHERE id = 1").fetchone()
    assert res['solde'] == 2500
    
    pari = db_settle.execute("SELECT statut FROM paris WHERE id = 50").fetchone()
    assert pari['statut'] == 'Gagné'

def test_pari_perdant(db_settle):
    db_settle.execute("UPDATE options SET winner = 2 WHERE id = 100")
    db_settle.commit()

    with patch('models.admin.envoi_notification_gain'):
        success, msg = executer_settlement_match(10)
    
    assert "1 perdus" in msg
    res = db_settle.execute("SELECT solde FROM parieurs WHERE id = 1").fetchone()
    assert res['solde'] == 1000
    
    pari = db_settle.execute("SELECT statut FROM paris WHERE id = 50").fetchone()
    assert pari['statut'] == 'Perdu'
