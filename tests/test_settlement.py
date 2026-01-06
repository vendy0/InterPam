import pytest
import sqlite3
from unittest.mock import patch
from models.admin import executer_settlement_match, valider_option_gagnante

# On crée une classe qui enveloppe la connexion pour ignorer l'appel à close()
class ConnectionWrapper:
    def __init__(self, conn):
        self.conn = conn

    def __getattr__(self, name):
        # Délègue les appels (comme execute, commit) à la vraie connexion
        return getattr(self.conn, name)

    def close(self):
        # On ne fait rien ici pour garder la base en mémoire vivante entre les appels
        pass

    # --- CES MÉTHODES DOIVENT ÊTRE DANS LA CLASSE ---
    def __enter__(self):
        # Permet d'utiliser "with get_db_connection() as conn:"
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Sortie du context manager
        pass
    # -----------------------------------------------

@pytest.fixture
def db_settle():
    """Base de données avec un parieur, un match et un pari combiné."""
    raw_conn = sqlite3.connect(":memory:")
    raw_conn.row_factory = sqlite3.Row
    
    # On enveloppe la connexion
    conn = ConnectionWrapper(raw_conn)

    conn.executescript("""
        CREATE TABLE parieurs (
            id INTEGER PRIMARY KEY, 
            solde INTEGER, 
            push_subscription TEXT
        );
        CREATE TABLE matchs (
            id INTEGER PRIMARY KEY, 
            equipe_a TEXT, 
            equipe_b TEXT, 
            statut TEXT
        );
        CREATE TABLE options (
            id INTEGER PRIMARY KEY, 
            match_id INTEGER, 
            winner INTEGER, 
            cote REAL, 
            categorie TEXT
        );
        CREATE TABLE paris (
            id INTEGER PRIMARY KEY, 
            parieur_id INTEGER, 
            mise INTEGER, 
            gain_potentiel INTEGER, 
            statut TEXT
        );
        CREATE TABLE matchs_paris (
            paris_id INTEGER, 
            matchs_id INTEGER, 
            option_id INTEGER
        );

        INSERT INTO parieurs (id, solde) VALUES (1, 1000); 
        INSERT INTO matchs (id, equipe_a, equipe_b, statut) VALUES (10, 'Haiti', 'Cuba', 'ouvert');
        INSERT INTO options (id, match_id, winner, cote, categorie) VALUES (100, 10, 0, 1.5, '1X2');
        
        INSERT INTO paris (id, parieur_id, mise, gain_potentiel, statut) VALUES (50, 1, 500, 1500, 'En attente');
        INSERT INTO matchs_paris (paris_id, matchs_id, option_id) VALUES (50, 10, 100);
    """)
    
    # On patche sqlite3.connect pour qu'il retourne notre wrapper
    # Ainsi, tout appel à get_db_connection() retournera cet objet qui supporte le 'with'
    with patch('sqlite3.connect', return_value=conn):
        yield conn
    raw_conn.close()


def test_pari_gagnant_et_paiement(db_settle):
    # 1. On valide l'option gagnante (utilise le wrapper via le patch de la fixture)
    valider_option_gagnante(100, 10)

    # 2. On exécute le settlement
    with patch('models.admin.envoi_notification_gain'):
        success, msg = executer_settlement_match(10)
    
    # 3. Vérifications
    assert success is True
    
    # Le solde doit être 1000 (initial) + 1500 (gain) = 2500
    res = db_settle.execute("SELECT solde FROM parieurs WHERE id = 1").fetchone()
    assert res['solde'] == 2500
    
    # Le statut du pari doit être 'Gagné'
    pari = db_settle.execute("SELECT statut FROM paris WHERE id = 50").fetchone()
    assert pari['statut'] == 'Gagné'

def test_pari_perdant(db_settle):
    # 1. On force l'option comme perdante (winner = 2)
    db_settle.execute("UPDATE options SET winner = 2 WHERE id = 100")
    db_settle.commit()

    # 2. On exécute le settlement
    with patch('models.admin.envoi_notification_gain'):
        success, msg = executer_settlement_match(10)
    
    # 3. Vérifications
    assert "perdus" in msg
    
    # Le solde ne doit pas bouger
    res = db_settle.execute("SELECT solde FROM parieurs WHERE id = 1").fetchone()
    assert res['solde'] == 1000
    
    # Le statut du pari doit être 'Perdu'
    pari = db_settle.execute("SELECT statut FROM paris WHERE id = 50").fetchone()
    assert pari['statut'] == 'Perdu'
