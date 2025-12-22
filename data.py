import sqlite3

DB_NAME = "interpam.db"


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
					solde REAL DEFAULT 1000.0,
					role TEXT DEFAULT 'parieur'
				)""")

            # Table Paris
            cur.execute("""CREATE TABLE IF NOT EXISTS paris (
					id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
					mise REAL NOT NULL,
					gain_potentiel REAL NOT NULL,
					date_pari TEXT NOT NULL,
					parieur_id INTEGER,
					FOREIGN KEY (parieur_id) REFERENCES parieurs(id) ON DELETE CASCADE
				)""")

            # Table Matchs
            cur.execute("""CREATE TABLE IF NOT EXISTS matchs (
					id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
					equipe_a TEXT NOT NULL,
					equipe_b TEXT NOT NULL,
					date_match TEXT NOT NULL UNIQUE,
					statut TEXT DEFAULT 'ouvert'
				)""")

            # Table matchs_paris
            cur.execute("""CREATE TABLE IF NOT EXISTS matchs_paris(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matchs_id INTEGER NOT NULL,
                paris_id INTEGER NOT NULL,
                option_id INTEGER NOT NULL, -- <-- Ajoute cette colonne
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
    except sqlite3.Error as e:
        print(f"Erreur lors de l'initialisation : {e}")



"""
---------------------------------------
RÉCUPÉRATION DE PARIEUR................
---------------------------------------
"""

# Récupération par Nom
def get_user_by_name(nom):
    """Récupère un utilisateur par son nom."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM parieurs WHERE prenom LIKE ? OR nom LIKE ?", (nom, nom))
            return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération (nom) : {e}")
        return None
        
# Récupération par Age
def get_user_by_age(age):
    """Récupère un utilisateur par son age."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM parieurs WHERE age = ?", (age,))
            return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération (age) : {e}")
        return None
        
# Récupération par Email
def get_user_by_email(email):
    """Récupère un utilisateur par son email (Tabulation 4)."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM parieurs WHERE email = ?", (email,))
            return cur.fetchone()
    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération (email) : {e}")
        return None

# Récupération par Username
def get_user_by_username(username):
    """Récupère un utilisateur par son username."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM parieurs WHERE username = ?", (username,))
            return cur.fetchone()
    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération (username) : {e}")
        return None
        
# Récupération par classe
def get_user_by_grade(classe):
    """Récupère un utilisateur par sa classe."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM parieurs WHERE classe = ?", (classe,))
            return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération (username) : {e}")
        return None

def filtrer_users_admin(criteres):
    """
    Recherche des utilisateurs correspondant à TOUS les critères fournis.
    'criteres' est un dictionnaire {colonne: valeur}
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # On ne garde que les champs qui ont une valeur
            filtres = {k: v for k, v in criteres.items() if v and v.strip() != ""}
            
            if not filtres:
                return []

            # Construction de la clause WHERE dynamique
            clauses = []
            parametres = []
            
            for col, val in filtres.items():
                if col in ["nom", "prenom"]: # Recherche floue pour les noms
                    clauses.append(f"{col} LIKE ?")
                    parametres.append(f"%{val}%")
                else: # Recherche exacte pour le reste (email, username, age, classe)
                    clauses.append(f"{col} = ?")
                    parametres.append(val)

            sql = f"SELECT * FROM parieurs WHERE {' AND '.join(clauses)}"
            
            cur.execute(sql, parametres)
            return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Erreur recherche dynamique : {e}")
        return []



"""
---------------------------------------
...
---------------------------------------
"""
def credit(username, solde):
	user = get_user_by_username(username)
	if not user:
		return False, "Utilisateur non trouvé !"
	new_solde = user["solde"] + solde
	try:
		with sqlite3.connect(DB_NAME) as conn:
			cur = conn.cursor()
			cur.execute("PRAGMA foreign_keys = ON")
			cur.execute("UPDATE parieurs SET solde = ? WHERE username = ?", (new_solde, username))
			print(f"Utilisateur {username} crédité de {solde} HTG. Nouveau solde : {new_solde}")
			return True, f"Utilisateur {username} crédité de {solde} HTG. Nouveau solde : {new_solde}"
	except sqlite3.Error as e:
			print(f"Erreur SQL lors de l'ajout du parieur : {e}")
	 


# Ajouter parieur
def ajouter_parieur(user_data):
    """Ajoute un parieur avec gestion d'exception et tabulation."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute(
                "INSERT INTO parieurs (prenom, nom, username, email, age, classe, mdp, created_at, solde) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_data["prenom"],
                    user_data["nom"],
                    user_data["username"],
                    user_data["email"],
                    user_data["age"],
                    user_data["classe"],
                    user_data["mdp"],
                    user_data["created_at"],
                    user_data["solde"],
                ),
            )
            print(f"Utilisateur {user_data['username']} ajouté.")
    except sqlite3.Error as e:
        print(f"Erreur SQL lors de l'ajout du parieur : {e}")


# Ajouter Match
def ajouter_match(equipe_a, equipe_b, date_match):
    """Ajoute un match avec bloc try-except et tabulation."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute(
                "INSERT INTO matchs (equipe_a, equipe_b, date_match) VALUES (?, ?, ?)",
                (equipe_a, equipe_b, date_match),
            )
            id_match = cur.lastrowid
            print(
                f"Match ajouté avec succès : {equipe_a} VS {equipe_b}, id : {id_match}"
            )
            return id_match
    except sqlite3.Error as e:
        print(f"Erreur lors de l'ajout du match : {e}")


# Ajouter Option
def ajouter_option(libelle, cote, categorie, match_id):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO options(libelle, cote, categorie, match_id) VALUES (?, ?, ?, ?)",
                (libelle, cote, categorie, match_id),
            )
            print(
                f"Option {libelle} x {cote} de la catégorie {categorie} créé avec succès."
            )
    except sqlite3.Error as e:
        print(f"Erreur lors de l'ajout : {e}")


# Récupération des Matchs au complet avec des matchs dupliqués
def get_matchs_complets():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""SELECT m.id AS match_id, m.equipe_a, m.equipe_b, m.date_match, o.libelle, o.id AS option_id, o.cote
            FROM matchs m
            INNER JOIN options o 
            ON m.id = o.match_id
            """)
            return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Une erreur s'est produite lors de la récupération : {e}")


# Récupération des Matchs en cours seulement avec des matchs dupliqués
def get_matchs_en_cours():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""SELECT m.id AS match_id, m.equipe_a, m.equipe_b, m.date_match, o.libelle, o.id AS option_id, o.cote, o.categorie
            FROM matchs m
            INNER JOIN options o 
            ON m.id = o.match_id
            WHERE m.statut = 'ouvert'
            """)
            return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Une erreur s'est produite lors de la récupération : {e}")


# Récupération des Matchs en cours avec les options liés grace à get_matchs_en_cours
def get_programmes():
    donnees = (
        get_matchs_en_cours()
    )  # Assure-toi que cette fonction utilise des alias SQL (AS match_id, etc.)
    programme = {}

    for ligne in donnees:
        m_id = ligne["match_id"]
        if m_id not in programme:
            programme[m_id] = {
                "equipe_a": ligne["equipe_a"],
                "equipe_b": ligne["equipe_b"],
                "date_match": ligne["date_match"],
                "match_id": m_id,
                "options": [],  # Cette liste va maintenant contenir des dictionnaires
            }

        # Création du dictionnaire d'option structuré
        if ligne["option_id"]:
            nouvelle_option = {
                "option_id": ligne[
                    "option_id"
                ],  # Crucial pour enregistrer le pari plus tard
                "libelle": ligne["libelle"],
                "cote": ligne["cote"],
                "categorie": ligne["categorie"],
            }

            programme[m_id]["options"].append(nouvelle_option)

    return programme


def placer_pari(parieur_id, match_id, mise, gain_potentiel, date_pari, options_ids):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("BEGIN TRANSACTION")

            # 1. On crée la fiche de pari principale
            cur.execute(
                """INSERT INTO paris(parieur_id, mise, gain_potentiel, date_pari)
                   VALUES (?, ?, ?, ?)""",
                (parieur_id, mise, gain_potentiel, date_pari),
            )
            paris_id = cur.lastrowid  # On récupère l'ID du pari qu'on vient de créer

            # 2. On enregistre chaque option choisie pour ce pari
            for opt_id in options_ids:
                cur.execute(
                    """INSERT INTO matchs_paris(matchs_id, paris_id, option_id) 
                       VALUES (?, ?, ?)""",
                    (match_id, paris_id, opt_id),
                )

            # 3. Mise à jour du solde du parieur (important !)
            cur.execute(
                "UPDATE parieurs SET solde = solde - ? WHERE id = ?", (mise, parieur_id)
            )

            cur.execute("COMMIT TRANSACTION")
            print("Pari effectué !")
            return True, "Pari effectué avec succès !"

    except sqlite3.Error as e:
        print(f"Erreur SQL : {e}")
        return False, f"Erreur lors du pari : {e}"


def obtenir_cotes_par_ids(liste_ids):
    """Retourne la liste des cotes pour les IDs fournis."""
    if not liste_ids:
        return []

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            # On prépare les points d'interrogation pour le IN (?, ?, ?)
            placeholders = ",".join(["?"] * len(liste_ids))
            requete = f"SELECT cote FROM options WHERE id IN ({placeholders})"

            cur.execute(requete, liste_ids)
            resultats = cur.fetchall()  # Retourne une liste de tuples [(1.5,), (2.0,)]

            return [r[0] for r in resultats]
    except sqlite3Error as e:
        print(f"Erreur SQL : {e}")
        return []
        
# Dans data.py
# from werkzeug.security import generate_password_hash
# from datetime import datetime

# def creer_super_admin(prenom, nom, username, email, mdp):
#     try:
#         with sqlite3.connect(DB_NAME) as conn:
#             cur = conn.cursor()
#             hash_mdp = generate_password_hash(mdp)
#             created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
#             cur.execute("""
#                 INSERT INTO parieurs (prenom, nom, username, email, age, classe, mdp, created_at, role, solde)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """, (prenom, nom, username, email, 99, "Direction", hash_mdp, created_at, 'super_admin', 0.0))
            
#             conn.commit()
#             return True, "Le Super Admin a été créé avec succès !"
#     except sqlite3.Error as e:
#         return False, f"Erreur lors de la création : {e}"
