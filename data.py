import sqlite3
from decimal import Decimal, ROUND_HALF_UP

DB_NAME = "interpam.db"


# --- UTILITAIRES DE CONVERSION ---
def vers_centimes(montant):
	"""Convertit un Decimal, float ou string en entier (centimes)"""
	if montant is None:
		return 0
	return int((Decimal(str(montant)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def depuis_centimes(centimes):
	"""Convertit un entier (centimes) en Decimal pour les calculs"""
	if centimes is None:
		return Decimal("0.00")
	return (Decimal(str(centimes)) / Decimal("100")).quantize(Decimal("0.01"))


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
                    solde INTEGER DEFAULT 100000,
                    role TEXT DEFAULT 'parieur'
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
                    statut TEXT DEFAULT 'ouvert'
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
	except sqlite3.Error as e:
		print(f"Erreur lors de l'initialisation : {e}")


"""
=======================================
2. GESTION DES UTILISATEURS (CRUD)-----
=======================================
"""


def ajouter_parieur(user_data):
	"""Ajoute un parieur avec gestion d'exception et tabulation."""
	try:
		with sqlite3.connect(DB_NAME) as conn:
			cur = conn.cursor()
			cur.execute("PRAGMA foreign_keys = ON")
			cur.execute(
				"INSERT INTO parieurs (prenom, nom, username, email, age, classe, mdp, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
				(
					user_data["prenom"],
					user_data["nom"],
					user_data["username"],
					user_data["email"],
					user_data["age"],
					user_data["classe"],
					user_data["mdp"],
					user_data["created_at"],
				),
			)
			print(f"Utilisateur {user_data['username']} ajouté.")
	except sqlite3.Error as e:
		print(f"Erreur SQL lors de l'ajout du parieur : {e}")


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


def get_user_by_email(email):
	"""Récupère un utilisateur par son email."""
	try:
		with sqlite3.connect(DB_NAME) as conn:
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()
			cur.execute("SELECT * FROM parieurs WHERE email = ?", (email,))
			user = cur.fetchone()
			if user:
				user_dict = dict(user)
				user_dict["solde"] = depuis_centimes(user_dict["solde"])
				return user_dict
			return None
	except sqlite3.Error as e:
		print(f"Erreur lors de la récupération (email) : {e}")
		return None


def get_user_by_username(username):
	"""Récupère un utilisateur par son username."""
	try:
		with sqlite3.connect(DB_NAME) as conn:
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()
			cur.execute("SELECT * FROM parieurs WHERE username = ?", (username,))
			user = cur.fetchone()
			if user:
				user_dict = dict(user)
				user_dict["solde"] = depuis_centimes(user_dict["solde"])
				return user_dict
			return None
	except sqlite3.Error as e:
		print(f"Erreur : {e}")
		return None


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
	"""Recherche des utilisateurs correspondant à TOUS les critères fournis."""
	try:
		with sqlite3.connect(DB_NAME) as conn:
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()

			filtres = {k: v for k, v in criteres.items() if v and v.strip() != ""}

			if not filtres:
				return []

			clauses = []
			parametres = []

			for col, val in filtres.items():
				if col in ["nom", "prenom", "username"]:
					clauses.append(f"{col} LIKE ?")
					parametres.append(f"%{val}%")
				else:
					clauses.append(f"{col} = ?")
					parametres.append(val)

			sql = f"SELECT * FROM parieurs WHERE {' AND '.join(clauses)}"
			cur.execute(sql, parametres)
			return cur.fetchall()
	except sqlite3.Error as e:
		print(f"Erreur recherche dynamique : {e}")
		return []


def credit(username, montant_decimal):
	"""Créditer un utilisateur (Accepte un montant Decimal)."""
	try:
		user = get_user_by_username(username)
		if not user:
			return False, "Utilisateur introuvable !"
		solde_centimes = vers_centimes(montant_decimal)
		with sqlite3.connect(DB_NAME) as conn:
			cur = conn.cursor()
			cur.execute(
				"UPDATE parieurs SET solde = solde + ? WHERE username = ?",
				(solde_centimes, username),
			)
			conn.commit()
			return True, "Compte crédité avec succès"
	except Exception as e:
		return False, str(e)


"""
========================================
3. GESTION DES MATCHS-------------------
========================================
"""


def ajouter_match(equipe_a, equipe_b, date_match):
	"""Ajoute un match."""
	try:
		with sqlite3.connect(DB_NAME) as conn:
			cur = conn.cursor()
			cur.execute("PRAGMA foreign_keys = ON")
			cur.execute(
				"INSERT INTO matchs (equipe_a, equipe_b, date_match) VALUES (?, ?, ?)",
				(equipe_a, equipe_b, date_match),
			)
			id_match = cur.lastrowid
			print(f"Match ajouté avec succès : {equipe_a} VS {equipe_b}, id : {id_match}")
			return id_match
	except sqlite3.Error as e:
		print(f"Erreur lors de l'ajout du match : {e}")


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


def get_programmes():
	donnees = get_matchs_en_cours()
	programme = {}

	for ligne in donnees:
		m_id = ligne["match_id"]
		if m_id not in programme:
			programme[m_id] = {
				"equipe_a": ligne["equipe_a"],
				"equipe_b": ligne["equipe_b"],
				"date_match": ligne["date_match"],
				"match_id": m_id,
				"options": [],
			}

		if ligne["option_id"]:
			nouvelle_option = {
				"option_id": ligne["option_id"],
				"libelle": ligne["libelle"],
				"cote": ligne["cote"],
				"categorie": ligne["categorie"],
			}
			programme[m_id]["options"].append(nouvelle_option)
	return programme


def get_all_matchs():
	try:
		with sqlite3.connect(DB_NAME) as conn:
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()
			cur.execute("""SELECT m.id AS match_id, m.equipe_a, m.equipe_b, m.date_match, o.libelle, o.id AS option_id, o.cote, o.categorie
            FROM matchs m
            INNER JOIN options o 
            ON m.id = o.match_id
            """)
			return cur.fetchall()
	except sqlite3.Error as e:
		print(f"Une erreur s'est produite lors de la récupération de tous les matchs : {e}")


def get_all_programmes():
	donnees = get_all_matchs()
	programme = {}

	for ligne in donnees:
		m_id = ligne["match_id"]
		if m_id not in programme:
			programme[m_id] = {
				"equipe_a": ligne["equipe_a"],
				"equipe_b": ligne["equipe_b"],
				"date_match": ligne["date_match"],
				"match_id": m_id,
				"options": [],
			}

		if ligne["option_id"]:
			nouvelle_option = {
				"option_id": ligne["option_id"],
				"libelle": ligne["libelle"],
				"cote": ligne["cote"],
				"categorie": ligne["categorie"],
			}
			programme[m_id]["options"].append(nouvelle_option)
	return programme


"""
========================================
4. GESTION DES OPTIONS DE PARIS---------
========================================
"""


def ajouter_option(libelle, cote, categorie, match_id):
	try:
		with sqlite3.connect(DB_NAME) as conn:
			cur = conn.cursor()
			cur.execute(
				"INSERT INTO options(libelle, cote, categorie, match_id) VALUES (?, ?, ?, ?)",
				(libelle, cote, categorie, match_id),
			)
			print(f"Option {libelle} x {cote} de la catégorie {categorie} créé avec succès.")
	except sqlite3.Error as e:
		print(f"Erreur lors de l'ajout : {e}")


def obtenir_cotes_par_ids(liste_ids):
	"""Retourne la liste des cotes pour les IDs fournis."""
	if not liste_ids:
		return []

	try:
		with sqlite3.connect(DB_NAME) as conn:
			cur = conn.cursor()
			placeholders = ",".join(["?"] * len(liste_ids))
			requete = f"SELECT cote FROM options WHERE id IN ({placeholders})"
			cur.execute(requete, liste_ids)
			resultats = cur.fetchall()
			return [r[0] for r in resultats]
	except sqlite3.Error as e:
		print(f"Erreur SQL : {e}")
		return []


def get_details_options_panier(liste_option_ids):
	"""Récupère les détails complets pour l'affichage du panier"""
	if not liste_option_ids:
		return []

	try:
		with sqlite3.connect(DB_NAME) as conn:
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()
			# On formate les ? pour le nombre d'IDs
			placeholders = ",".join(["?"] * len(liste_option_ids))
			sql = f"""
                SELECT o.id as option_id, o.libelle, o.cote, o.categorie,
                       m.id as match_id, m.equipe_a, m.equipe_b, m.date_match
                FROM options o
                JOIN matchs m ON o.match_id = m.id
                WHERE o.id IN ({placeholders})
            """
			cur.execute(sql, liste_option_ids)
			return cur.fetchall()
	except sqlite3.Error as e:
		print(f"Erreur panier : {e}")
		return []


"""
========================================
5. SYSTÈME DE PARIS---------------------
========================================
"""


def placer_pari(parieur_id, match_id, mise_dec, gain_dec, date_pari, options_ids):
	"""
	place un pari
	- mise_dec : Decimal (HTG)
	- gain_dec : Decimal (HTG)
	- BDD : centimes (INTEGER)
	"""
	try:
		# --- Conversion UNIQUE Decimal -> centimes ---
		mise_c = vers_centimes(mise_dec)
		gain_c = vers_centimes(gain_dec)

		with sqlite3.connect(DB_NAME) as conn:
			cur = conn.cursor()
			cur.execute("BEGIN TRANSACTION")

			# --- Vérification solde ---
			cur.execute("SELECT solde FROM parieurs WHERE id = ?", (parieur_id,))
			row = cur.fetchone()
			if not row:
				return False, "Parieur introuvable"

			solde_c = row[0]
			if solde_c < mise_c:
				return False, "Solde insuffisant"

			# --- Débit du solde ---
			cur.execute(
				"UPDATE parieurs SET solde = solde - ? WHERE id = ?",
				(mise_c, parieur_id),
			)

			# --- Création du pari ---
			cur.execute(
				"""
                INSERT INTO paris (mise, gain_potentiel, date_pari, parieur_id)
                VALUES (?, ?, ?, ?)
                """,
				(mise_c, gain_c, date_pari, parieur_id),
			)
			pari_id = cur.lastrowid

			# --- Liaison options ---
			for opt_id in options_ids:
				cur.execute(
					"INSERT INTO matchs_paris (paris_id, matchs_id, option_id) VALUES (?, ?, ?)",
					(pari_id, match_id, opt_id),
				)

			conn.commit()
			return True, "Pari placé avec succès"

	except Exception as e:
		return False, f"Erreur lors du pari : {e}"


def get_fiches(parieur_id):
	try:
		with sqlite3.connect(DB_NAME) as conn:
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()
			cur.execute(
				"SELECT * FROM paris WHERE parieur_id = ? ORDER BY date_pari DESC",
				(parieur_id,),
			)
			return cur.fetchall()
	except sqlite3.Error as e:
		print(f"Erreur lors de la récupération des paris : {e}")
		return None


def get_fiches_detaillees(parieur_id):
	try:
		with sqlite3.connect(DB_NAME) as conn:
			conn.row_factory = sqlite3.Row
			cur = conn.cursor()
			query = """
                SELECT 
                p.id AS pari_id, p.mise, p.gain_potentiel, p.date_pari, m.equipe_a, m.equipe_b, m.date_match, o.libelle AS option_nom, o.cote
                FROM paris p 
                JOIN matchs_paris mp 
                ON p.id = mp.paris_id 
                JOIN options o ON mp.option_id = o.id 
                JOIN matchs m ON o.match_id = m.id 
                WHERE p.parieur_id = ? 
                ORDER BY p.date_pari DESC
            """
			cur.execute(query, (parieur_id,))
			lignes = cur.fetchall()

			fiches = {}
			for ligne in lignes:
				p_id = ligne["pari_id"]
				if p_id not in fiches:
					fiches[p_id] = {
						"mise": ligne["mise"],
						"gain": ligne["gain_potentiel"],
						"date": ligne["date_pari"],
						"selections": [],
					}
				fiches[p_id]["selections"].append(
					{
						"equipe_a": ligne["equipe_a"],
						"equipe_b": ligne["equipe_b"],
						"option": ligne["option_nom"],
						"cote": ligne["cote"],
					}
				)
			return fiches
	except sqlite3.Error as e:
		print(f"Erreur SQL fiches détaillées : {e}")
		return {}


# from werkzeug.security import generate_password_hash
# from datetime import datetime
# def creer_super_admin(prenom, nom, username, email, mdp):
#     try:
#         with sqlite3.connect(DB_NAME) as conn:
#             cur = conn.cursor()
#             hash_mdp = generate_password_hash(mdp)
#             created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#             cur.execute(
#                 """
#                 INSERT INTO parieurs (prenom, nom, username, email, age, classe, mdp, created_at, role, solde)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#             """,
#                 (
#                     prenom,
#                     nom,
#                     username,
#                     email,
#                     99,
#                     "Direction",
#                     hash_mdp,
#                     created_at,
#                     "super_admin",
#                     200000,
#                 ),
#             )

#             conn.commit()
#             return True, "Le Super Admin a été créé avec succès !"
#     except sqlite3.Error as e:
#         return False, f"Erreur lors de la création : {e}"
