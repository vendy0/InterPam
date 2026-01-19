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
                    type_match TEXT DEFAULT 'foot',
                    admin_id INTEGER,
                    FOREIGN KEY (admin_id) REFERENCES parieurs(id) ON DELETE SET NULL
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

			# Table Transactions (Dépôts et Retraits)
			# setup.py (Version améliorée)

			# cur.execute("""CREATE TABLE IF NOT EXISTS transactions (
            #         id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            #         user_id INTEGER NOT NULL,
            #         admin_id INTEGER, 
            #         type TEXT NOT NULL, 
            #         montant INTEGER NOT NULL, 
            #         frais INTEGER DEFAULT 0,  
            #         montant_net INTEGER DEFAULT 0,
            #         telephone TEXT NOT NULL,
            #         moncash_id TEXT UNIQUE,
            #         statut TEXT DEFAULT 'en_attente', 
            #         created_at TEXT NOT NULL,
            #         processed_at TEXT,
            #         raison_refus TEXT, 
            #         FOREIGN KEY (user_id) REFERENCES parieurs(id) ON DELETE CASCADE,
            #         FOREIGN KEY (admin_id) REFERENCES parieurs(id)
            #     )""")

			cur.execute("""CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    montant INTEGER NOT NULL, 
                    frais INTEGER DEFAULT 0,
                    montant_net INTEGER DEFAULT 0,
                    processed_at TEXT,
                    envoyeur_id INTEGER,
                    receveur_id INTEGER,
                    FOREIGN KEY (envoyeur_id) REFERENCES parieurs(id) ON DELETE SET NULL,
                    FOREIGN KEY (receveur_id) REFERENCES parieurs(id) ON DELETE SET NULL
                )""")

			# Table des inscriptions avant confirmation
			cur.execute("""CREATE TABLE IF NOT EXISTS pending_registrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    prenom TEXT NOT NULL,
                    nom TEXT NOT NULL,
                    username TEXT NOT NULL,
                    email TEXT NOT NULL,
                    age INT NOT NULL,
                    classe TEXT NOT NULL,
                    mdp TEXT NOT NULL,
                    token TEXT NOT NULL,
                    expiration TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )""")

			# Table des interventions manuelles (Crédit/Débit par admin)
			cur.execute("""CREATE TABLE IF NOT EXISTS admin_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    admin_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL, -- 'credit' ou 'debit'
                    montant INTEGER NOT NULL, -- En centimes
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (admin_id) REFERENCES parieurs(id),
                    FOREIGN KEY (user_id) REFERENCES parieurs(id)
                )""")

			# Table Configuration (Caisse, Limites, Frais)
			cur.execute("""CREATE TABLE IF NOT EXISTS config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    caisse_solde INTEGER DEFAULT 200000,  -- En centimes (ex: 2,000 HTG)
                    mise_min INTEGER DEFAULT 1000,         -- En centimes (ex: 10 HTG)
                    mise_max INTEGER DEFAULT 100000,       -- En centimes (ex: 1,000 HTG)
                    frais_retrait REAL DEFAULT 0.03        -- 3%
                )""")

			cur.execute(
				"INSERT OR IGNORE INTO config (id, caisse_solde, mise_min, mise_max, frais_retrait) VALUES (1, 200000, 1000, 100000, 0.03)"
			)

            # cur.execute("""CREATE TABLE IF NOT EXISTS 
            
            # )""")

	except sqlite3.Error as e:
		print(f"Erreur lors de l'initialisation : {e}")
