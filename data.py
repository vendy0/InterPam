import sqlite3
from decimal import Decimal, ROUND_HALF_UP

DB_NAME = "interpam.db"


# --- UTILITAIRES DE CONVERSION ---
def vers_centimes(montant):
    """Convertit un Decimal, float ou string en entier (centimes)"""
    if montant is None:
        return 0
    return int(
        (Decimal(str(montant)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


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
            cur.execute(
                "SELECT * FROM parieurs WHERE prenom LIKE ? OR nom LIKE ?", (nom, nom)
            )
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


def get_all_users():
    """Récupérer tous les utilisateurs."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM parieurs ORDER BY prenom ASC")
            return cur.fetchall()
    except Exception as e:
        return f"Erreur lors de la récupération : {e}"


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
            print(
                f"Match ajouté avec succès : {equipe_a} VS {equipe_b}, id : {id_match}"
            )
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
            cur.execute("""SELECT m.id AS match_id, m.equipe_a, m.equipe_b, m.type_match, m.date_match, m.statut, o.libelle, o.id AS option_id, o.cote, o.categorie
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
                "statut": ligne["statut"],
                "type_match": ligne["type_match"],
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
        print(
            f"Une erreur s'est produite lors de la récupération de tous les matchs : {e}"
        )


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


# --- AJOUTS DANS data.py ---


def get_match_by_id(match_id):
    """Récupère les infos brutes d'un match par son ID."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM matchs WHERE id = ?", (match_id,))
            return cur.fetchone()
    except sqlite3.Error as e:
        print(f"Erreur get_match_by_id : {e}")
        return None


def get_options_by_match_id(match_id):
    """Récupère toutes les options liées à un match."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM options WHERE match_id = ?", (match_id,))
            return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Erreur get_options_by_match_id : {e}")
        return []


def update_match_info(match_id, equipe_a, equipe_b, date_match, statut, type_match):
    """Met à jour les informations générales du match."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE matchs 
                SET equipe_a = ?, equipe_b = ?, date_match = ?, statut = ?, type_match = ?
                WHERE id = ?
            """,
                (equipe_a, equipe_b, date_match, statut, type_match, match_id),
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Erreur update_match_info : {e}")
        return False


def update_option_info(option_id, libelle, cote, categorie):
    """Met à jour une option existante."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE options 
                SET libelle = ?, cote = ?, categorie = ?
                WHERE id = ?
            """,
                (libelle, cote, categorie, option_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        print(f"Erreur update_option_info : {e}")


def get_all_matchs_ordonnes():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            # Tri par statut (ouvert/fermé) puis par date
            cur.execute("""
                SELECT id AS match_id, equipe_a, equipe_b, date_match, statut, type_match
                FROM matchs
                WHERE statut <> 'terminé'
                ORDER BY statut DESC, date_match ASC
            """)
            matchs = cur.fetchall()

            # Transformer en dictionnaire format "programme" pour le template
            programme = {}
            for m in matchs:
                programme[m["match_id"]] = dict(m)
            return programme
    except sqlite3.Error as e:
        print(f"Erreur récupération ordonnée : {e}")
        return {}


def valider_option_gagnante(option_id, match_id):
    """
    Met l'option à 1 (gagné) et les autres options de la même
    catégorie pour ce match à 2 (perdu).
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            # 1. Récupérer la catégorie de l'option choisie
            cur.execute("SELECT categorie FROM options WHERE id = ?", (option_id,))
            res = cur.fetchone()
            if not res:
                return False
            categorie = res[0]

            # 2. Mettre toutes les options de cette catégorie pour ce match à 2 (perdu)
            cur.execute(
                """
                UPDATE options SET winner = 2 
                WHERE match_id = ? AND categorie = ?
            """,
                (match_id, categorie),
            )

            # 3. Mettre l'option spécifique à 1 (gagné)
            cur.execute("UPDATE options SET winner = 1 WHERE id = ?", (option_id,))

            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Erreur validation : {e}")
        return False


def fermer_match_officiellement(match_id):
    """Change le statut du match pour qu'il ne soit plus modifiable."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE matchs SET statut = 'terminé' WHERE id = ?", (match_id,)
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Erreur fermeture match : {e}")
        return False

def get_matchs_actifs():
    """Récupère uniquement les matchs qui ne sont pas encore terminés/payés."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT id AS match_id, equipe_a, equipe_b, date_match, statut, type_match 
                FROM matchs 
                WHERE statut != 'terminé'
                ORDER BY date_match ASC
            """)
            matchs = cur.fetchall()
            return {m['match_id']: dict(m) for m in matchs}
    except sqlite3.Error as e:
        print(f"Erreur : {e}")
        return {}


def get_historique_matchs():
    """Récupère uniquement les matchs terminés."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT id AS match_id, equipe_a, equipe_b, date_match, statut, type_match 
                FROM matchs 
                WHERE statut = 'terminé'
                ORDER BY date_match DESC
            """)
            matchs = cur.fetchall()
            return {m["match_id"]: dict(m) for m in matchs}
    except sqlite3.Error as e:
        print(f"Erreur : {e}")
        return {}


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
            print(
                f"Option {libelle} x {cote} de la catégorie {categorie} créé avec succès."
            )
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
                p.id AS pari_id, p.mise, p.gain_potentiel, p.date_pari, p.statut, m.equipe_a, m.equipe_b, m.date_match, o.libelle AS option_nom, o.cote, o.winner, o.categorie
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
                        "statut": ligne["statut"],
                        "selections": [],
                    }
                fiches[p_id]["selections"].append(
                    {
                        "equipe_a": ligne["equipe_a"],
                        "equipe_b": ligne["equipe_b"],
                        "option": ligne["option_nom"],
                        "cote": ligne["cote"],
                        "status_option": ligne["winner"],
                        "categorie": ligne["categorie"],
                    }
                )
            return fiches
    except sqlite3.Error as e:
        print(f"Erreur SQL fiches détaillées : {e}")
        return {}


def verifier_matchs_ouverts(liste_option_ids):
    """Vérifie si tous les matchs liés aux options fournies sont encore 'ouvert'."""
    if not liste_option_ids:
        return False

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            placeholders = ",".join(["?"] * len(liste_option_ids))
            # On compte combien d'options pointent vers un match dont le statut n'est pas 'ouvert'
            sql = f"""
                SELECT COUNT(*) 
                FROM options o
                JOIN matchs m ON o.match_id = m.id
                WHERE o.id IN ({placeholders}) AND m.statut != 'ouvert'
            """
            cur.execute(sql, liste_option_ids)
            matchs_fermes = cur.fetchone()[0]
            # Si le compte est 0, cela signifie que tout est 'ouvert'
            return matchs_fermes == 0
    except sqlite3.Error as e:
        print(f"Erreur vérification statut : {e}")
        return False


"""
========================================
6. SETTLEMENT---------------------------
========================================
"""


def executer_settlement_match(match_id):
    """
    Vérifie les paris liés au match et effectue le paiement si nécessaire.
    Version corrigée et sécurisée.
    """
    conn = None
    try:
        # On utilise le context manager pour la connexion, mais on gère le commit manuellement
        # pour s'assurer que tout ou rien n'est exécuté.
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()

        # 1. Récupérer tous les paris "En attente" liés à ce match
        cur.execute(
            """
            SELECT DISTINCT p.id, p.parieur_id, p.gain_potentiel
            FROM paris p
            JOIN matchs_paris mp ON p.id = mp.paris_id
            WHERE mp.matchs_id = ? AND p.statut = 'En attente'
        """,
            (match_id,),
        )

        paris_a_verifier = cur.fetchall()
        stats = {"gagnants": 0, "perdants": 0, "erreurs": 0}

        if not paris_a_verifier:
            conn.close()
            return True, "Aucun pari en attente pour ce match."

        for p_id, user_id, gain_c in paris_a_verifier:
            # 2. Analyser l'état de TOUTES les options du ticket (pas seulement ce match)
            cur.execute(
                """
                SELECT 
                    COUNT(*) as total_options,
                    COALESCE(SUM(CASE WHEN o.winner = 2 THEN 1 ELSE 0 END), 0) as nb_perdues,
                    COALESCE(SUM(CASE WHEN o.winner = 1 THEN 1 ELSE 0 END), 0) as nb_gagnees
                FROM matchs_paris mp
                JOIN options o ON mp.option_id = o.id
                WHERE mp.paris_id = ?
            """,
                (p_id,),
            )

            row = cur.fetchone()
            if not row:
                continue

            total, perdues, gagnees = row[0], row[1], row[2]

            # LOGIQUE DE RÉSOLUTION
            if perdues > 0:
                # Si AU MOINS UNE option est perdante, tout le ticket est perdu
                cur.execute("UPDATE paris SET statut = 'Perdu' WHERE id = ?", (p_id,))
                stats["perdants"] += 1

            elif gagnees == total and total > 0:
                # Si TOUTES les options sont gagnantes (et qu'il y en a au moins une)
                # 1. Créditer le parieur
                cur.execute(
                    "UPDATE parieurs SET solde = solde + ? WHERE id = ?",
                    (gain_c, user_id),
                )
                # 2. Marquer le pari comme gagné
                cur.execute("UPDATE paris SET statut = 'Gagné' WHERE id = ?", (p_id,))
                stats["gagnants"] += 1

            # Sinon, le pari reste "En attente" (en attente d'autres matchs du combiné)

        conn.commit()
        conn.close()

        return (
            True,
            f"Settlement terminé : {stats['gagnants']} payés, {stats['perdants']} perdus.",
        )

    except sqlite3.Error as e:
        if conn:
            conn.rollback()
            conn.close()
        print(f"Erreur CRITIQUE settlement : {e}")
        return False, f"Erreur base de données : {e}"
    except Exception as e:
        if conn:
            conn.close()
        return False, f"Erreur inattendue : {e}"


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


def ajouter_column():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("ALTER TABLE matchs ADD COLUMN type_match TEXT DEFAULT 'foot'")
            conn.commit()
    except sqlite3.Error as e:
        print(f"Erreur lors de l'ajout de la colonne : {e}")
        return None


# def update():
#     try:
#         with sqlite3.connect(DB_NAME) as conn:
#             cur = conn.cursor()
#             cur.execute("ALTER TABLE matchs RENAME COLUMN type TO type_match")
#             conn.commit()
#     except sqlite3.Error as e:
#         print(f"Erreur lors de l'ajout de la renommation : {e}")
#         return None
