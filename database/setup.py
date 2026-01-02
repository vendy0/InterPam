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

            # Table Messagerie
            cur.execute("""CREATE TABLE IF NOT EXISTS messagerie (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    message TEXT NOT NULL,
                    read INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    parieur_id INTEGER,
                    FOREIGN KEY (parieur_id) REFERENCES parieurs(id) ON DELETE SET NULL
                    )""")

    except sqlite3.Error as e:
        print(f"Erreur lors de l'initialisation : {e}")


"""
========================================
2. CREATE SUPER ADMIN-------------------
========================================
"""
# Create Super Admin

from werkzeug.security import generate_password_hash
from datetime import datetime


def creer_super_admin(prenom, nom, username, email, mdp):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            hash_mdp = generate_password_hash(mdp)
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cur.execute(
                """
                INSERT INTO parieurs (prenom, nom, username, email, age, classe, mdp, created_at, role, solde)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    prenom,
                    nom,
                    username,
                    email,
                    99,
                    "Direction",
                    hash_mdp,
                    created_at,
                    "super_admin",
                    200000,
                ),
            )

            conn.commit()
            return True, "Le Super Admin a été créé avec succès !"
    except sqlite3.Error as e:
        return False, f"Erreur lors de la création : {e}"
