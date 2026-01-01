import sqlite3

DB_NAME = "interpam.db"


"""
========================================
1. CONFIGURATION------------------------
========================================
"""


def initialiser_bdd():
    """Initialise les tables de la base de données."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON")

            # Table parieurs
            cur.execute("""CREATE TABLE IF NOT EXISTS parieurs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    prenom TEXT NOT NULL,
                    nom TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    age INT NOT NULL,
                    classe TEXT NOT NULL,
                    mdp TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    solde INTEGER DEFAULT 0,
                    role TEXT DEFAULT 'parieur',
                    push_subscription TEXT,
                    actif INTEGER DEFAULT 1
                )""")

            # Table Paris
            cur.execute("""CREATE TABLE IF NOT EXISTS paris (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    mise INTEGER NOT NULL,
                    gain_potentiel INTEGER NOT NULL,
                    date_pari TEXT NOT NULL,
                    statut TEXT DEFAULT 'En attente',
                    parieur_id INTEGER,
                    FOREIGN KEY (parieur_id) REFERENCES parieurs(id) ON DELETE CASCADE
                )""")

            # Table Matchs
            cur.execute("""CREATE TABLE IF NOT EXISTS matchs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    equipe_a TEXT NOT NULL,
                    equipe_b TEXT NOT NULL,
                    date_match TEXT NOT NULL,
                    statut TEXT DEFAULT 'ouvert',
                    type_match TEXT DEFAULT 'foot'
                )""")

            # Table matchs_paris
            cur.execute("""CREATE TABLE IF NOT EXISTS matchs_paris(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matchs_id INTEGER NOT NULL,
                paris_id INTEGER NOT NULL,
                option_id INTEGER NOT NULL,
                FOREIGN KEY (matchs_id) REFERENCES matchs(id),
                FOREIGN KEY (paris_id) REFERENCES paris(id),
                FOREIGN KEY (option_id) REFERENCES options(id)
            )""")

            # Table Options
            cur.execute("""CREATE TABLE IF NOT EXISTS options (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    libelle TEXT NOT NULL,
                    cote REAL NOT NULL,
                    winner INTEGER DEFAULT 0,
                    categorie TEXT NOT NULL,
                    match_id INTEGER NOT NULL,
                    FOREIGN KEY (match_id) REFERENCES matchs(id) ON DELETE CASCADE
                )""")

            # Table Invitations
            cur.execute("""CREATE TABLE IF NOT EXISTS invitations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    email TEXT NOT NULL,
                    role TEXT NOT NULL,
                    token TEXT NOT NULL,
                    expiration TEXT NOT NULL
                )""")

            # Table Recupération_mdp
            cur.execute("""CREATE TABLE IF NOT EXISTS recuperations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    email TEXT NOT NULL,
                    token TEXT NOT NULL,
                    expiration TEXT NOT NULL
                )""")

    except sqlite3.Error as e:
        print(f"Erreur lors de l'initialisation : {e}")
