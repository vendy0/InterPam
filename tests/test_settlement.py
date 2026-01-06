import pytest
import sqlite3
import os
from database.setup import (
    initialiser_bdd,
    DB_NAME,
)  # Assure-toi que setup.py est importable
# Importe ta fonction ici (ajuste le nom du module si nécessaire)
# from ton_script_principal import executer_settlement_match


@pytest.fixture
def db_session():
    """Crée une base de données propre pour chaque test."""
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    initialiser_bdd()

    conn = sqlite3.connect(DB_NAME)
    yield conn
    conn.close()
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)


def test_settlement_gagne(db_session):
    cur = db_session.cursor()
    # 1. Créer un parieur (Solde initial 1000)
    cur.execute(
        "INSERT INTO parieurs (prenom, nom, username, email, age, classe, mdp, created_at, solde) VALUES ('Test', 'User', 'testuser', 'test@test.com', 20, '1A', 'hash', 'now', 1000)"
    )
    user_id = cur.lastrowid

    # 2. Créer un match et une option gagnante
    cur.execute(
        "INSERT INTO matchs (equipe_a, equipe_b, date_match, statut) VALUES ('Real', 'Barca', '2026-01-01', 'termine')"
    )
    match_id = cur.lastrowid
    cur.execute(
        "INSERT INTO options (libelle, cote, winner, categorie, match_id) VALUES ('Victoire A', 2.0, 1, 'score', ?)",
        (match_id,),
    )
    option_id = cur.lastrowid

    # 3. Créer un pari (Mise 100, Gain 200)
    cur.execute(
        "INSERT INTO paris (mise, gain_potentiel, date_pari, statut, parieur_id) VALUES (100, 200, 'now', 'En attente', ?)",
        (user_id,),
    )
    pari_id = cur.lastrowid
    cur.execute(
        "INSERT INTO matchs_paris (matchs_id, paris_id, option_id) VALUES (?, ?, ?)",
        (match_id, pari_id, option_id),
    )
    db_session.commit()

    # 4. Exécuter le settlement
    from models.admin import (
        executer_settlement_match,
    )  # Remplace 'models.admin' par le nom de ton fichier

    success, message = executer_settlement_match(match_id)

    # 5. Vérifications
    cur.execute("SELECT statut FROM paris WHERE id = ?", (pari_id,))
    assert cur.fetchone()[0] == "Gagné"
    cur.execute("SELECT solde FROM parieurs WHERE id = ?", (user_id,))
    assert cur.fetchone()[0] == 1200  # 1000 + 200 de gain


def test_settlement_perdu(db_session):
    cur = db_session.cursor()
    cur.execute(
        "INSERT INTO parieurs (prenom, nom, username, email, age, classe, mdp, created_at, solde) VALUES ('Locker', 'User', 'loser', 'lost@test.com', 20, '1A', 'hash', 'now', 1000)"
    )
    user_id = cur.lastrowid

    cur.execute(
        "INSERT INTO matchs (equipe_a, equipe_b, date_match) VALUES ('PSG', 'OM', 'now')"
    )
    m_id = cur.lastrowid
    cur.execute(
        "INSERT INTO options (libelle, cote, winner, categorie, match_id) VALUES ('Victoire B', 3.0, 2, 'score', ?)",
        (m_id,),
    )
    o_id = cur.lastrowid

    cur.execute(
        "INSERT INTO paris (mise, gain_potentiel, date_pari, statut, parieur_id) VALUES (50, 150, 'now', 'En attente', ?)",
        (user_id,),
    )
    p_id = cur.lastrowid
    cur.execute(
        "INSERT INTO matchs_paris (matchs_id, paris_id, option_id) VALUES (?, ?, ?)",
        (m_id, p_id, o_id),
    )
    db_session.commit()

    from models.admin import executer_settlement_match

    executer_settlement_match(m_id)

    cur.execute("SELECT statut FROM paris WHERE id = ?", (p_id,))
    assert cur.fetchone()[0] == "Perdu"
    cur.execute("SELECT solde FROM parieurs WHERE id = ?", (user_id,))
    assert (
        cur.fetchone()[0] == 1000
    )  # Le solde ne bouge pas (la mise a déjà été retirée lors du placement du pari)


def test_settlement_annule_remboursement(db_session):
    cur = db_session.cursor()
    cur.execute(
        "INSERT INTO parieurs (prenom, nom, username, email, age, classe, mdp, created_at, solde) VALUES ('Refund', 'User', 'ref', 'ref@test.com', 20, '1A', 'hash', 'now', 500)"
    )
    user_id = cur.lastrowid

    cur.execute(
        "INSERT INTO matchs (equipe_a, equipe_b, date_match) VALUES ('Team A', 'Team B', 'now')"
    )
    m_id = cur.lastrowid
    # winner = 3 (Annulé)
    cur.execute(
        "INSERT INTO options (libelle, cote, winner, categorie, match_id) VALUES ('Draw', 3.0, 3, 'score', ?)",
        (m_id,),
    )
    o_id = cur.lastrowid

    # Dans ce cas, gain_potentiel est souvent ajusté à la mise (ex: 100)
    cur.execute(
        "INSERT INTO paris (mise, gain_potentiel, date_pari, statut, parieur_id) VALUES (100, 100, 'now', 'En attente', ?)",
        (user_id,),
    )
    p_id = cur.lastrowid
    cur.execute(
        "INSERT INTO matchs_paris (matchs_id, paris_id, option_id) VALUES (?, ?, ?)",
        (m_id, p_id, o_id),
    )
    db_session.commit()

    from models.admin import executer_settlement_match

    executer_settlement_match(m_id)

    cur.execute("SELECT statut FROM paris WHERE id = ?", (p_id,))
    assert cur.fetchone()[0] == "Annulé"
    cur.execute("SELECT solde FROM parieurs WHERE id = ?", (user_id,))
    assert cur.fetchone()[0] == 600  # 500 + 100 remboursé
