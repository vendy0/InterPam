from database.connexion import get_db_connection
import sqlite3
from models.emails import envoyer_push_notification


def get_options_by_match_id(match_id):
    """Récupère toutes les options liées à un match."""
    try:
        with get_db_connection() as conn:
            cur = conn.execute("SELECT * FROM options WHERE match_id = ?", (match_id,))
            return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Erreur get_options_by_match_id : {e}")
        return []


def get_matchs_en_cours():
    try:
        with get_db_connection() as conn:
            cur = conn.execute("""SELECT m.id AS match_id, m.equipe_a, m.equipe_b, m.type_match, m.date_match, m.statut, o.libelle, o.id AS option_id, o.cote, o.categorie
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
    if not donnees:
        return None
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


def get_match_by_id(match_id):
    """Récupère les infos brutes d'un match par son ID."""
    try:
        with get_db_connection() as conn:
            cur = conn.execute("SELECT * FROM matchs WHERE id = ?", (match_id,))
            return cur.fetchone()
    except sqlite3.Error as e:
        print(f"Erreur get_match_by_id : {e}")
        return None


def get_options_by_match_id(match_id):
    """Récupère toutes les options liées à un match."""
    try:
        with get_db_connection() as conn:
            cur = conn.execute("SELECT * FROM options WHERE match_id = ?", (match_id,))
            return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Erreur get_options_by_match_id : {e}")
        return []


def get_all_matchs_ordonnes():
    try:
        with get_db_connection() as conn:
            # Tri par statut (ouvert/fermé) puis par date
            cur = conn.execute("""
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


def get_matchs_actifs():
    """Récupère uniquement les matchs qui ne sont pas encore terminés/payés."""
    try:
        with get_db_connection() as conn:
            cur = conn.execute("""
                SELECT id AS match_id, equipe_a, equipe_b, date_match, statut, type_match 
                FROM matchs 
                WHERE statut != 'terminé' AND statut != 'annulé'
                ORDER BY date_match ASC
            """)
            matchs = cur.fetchall()
            return {m["match_id"]: dict(m) for m in matchs}
    except sqlite3.Error as e:
        print(f"Erreur : {e}")
        return {}


def get_historique_matchs():
    """Récupère uniquement les matchs terminés."""
    try:
        with get_db_connection() as conn:
            cur = conn.execute("""
                SELECT m.id AS match_id, m.equipe_a, m.equipe_b, m.date_match, m.statut, m.type_match, p.prenom AS admin_prenom, p.nom AS admin_nom
                FROM matchs  m
                LEFT JOIN parieurs p ON m.admin_id = p.id
                WHERE statut = 'terminé' OR statut = 'annulé'
                ORDER BY date_match DESC
            """)
            matchs = cur.fetchall()
            return {m["match_id"]: dict(m) for m in matchs}
    except sqlite3.Error as e:
        print(f"Erreur : {e}")
        return {}


# Dans models/match.py


def get_historique_complet(user_id):
    """
    Récupère les matchs terminés, toutes les options associées,
    et marque celles jouées par l'utilisateur.
    """
    try:
        with get_db_connection() as conn:
            # 1. Récupérer les matchs terminés
            cur = conn.execute("""
                SELECT id, equipe_a, equipe_b, date_match, score_a, score_b 
                FROM matchs 
                WHERE statut = 'terminé' 
                ORDER BY date_match DESC
            """)
            matchs = [dict(row) for row in cur.fetchall()]

            # 2. Récupérer les IDs des options jouées par l'utilisateur
            # ADAPTE 'paris' et 'paris_details' selon ta structure réelle (ex: selections, tickets...)
            user_options_query = """
                SELECT mp.option_id 
                FROM matchs_paris mp
                JOIN paris p ON mp.paris_id = p.id
                WHERE p.parieur_id = ?
            """
            # Si ta table s'appelle autrement, modifie juste la ligne au dessus
            try:
                cur_user = conn.execute(user_options_query, (user_id,))
                user_played_ids = {row["option_id"] for row in cur_user.fetchall()}
            except sqlite3.Error:
                # Si la table n'existe pas encore ou erreur, on met une liste vide pour ne pas crasher
                user_played_ids = set()

            # 3. Pour chaque match, récupérer ses options
            resultat = []
            for m in matchs:
                cur_opt = conn.execute(
                    "SELECT * FROM options WHERE match_id = ?", (m["id"],)
                )
                options = [dict(row) for row in cur_opt.fetchall()]

                # Ajouter l'info "joué par user" à chaque option
                for opt in options:
                    opt["user_played"] = opt["id"] in user_played_ids

                m["options"] = options
                resultat.append(m)

            return resultat

    except sqlite3.Error as e:
        print(f"Erreur historique : {e}")
        return []


def get_tous_les_resultats(user_id):
    """
    Récupère les matchs terminés, toutes les options associées,
    et marque celles jouées par l'utilisateur.
    """
    try:
        with get_db_connection() as conn:
            # 1. Récupérer les matchs terminés
            # Note : Assure-toi que les colonnes score_a et score_b existent bien dans ta table matchs
            cur = conn.execute("""
                SELECT id, equipe_a, equipe_b, date_match, statut 
                FROM matchs 
                WHERE statut = 'terminé' 
                ORDER BY date_match DESC
            """)
            matchs = [dict(row) for row in cur.fetchall()]

            # 2. Récupérer les IDs des options jouées par l'utilisateur
            # RECTIFICATION : On utilise 'paris_id' (vu dans setup.py)
            user_options_query = """
                SELECT mp.option_id 
                FROM matchs_paris mp
                JOIN paris p ON mp.paris_id = p.id
                WHERE p.parieur_id = ?
            """

            try:
                cur_user = conn.execute(user_options_query, (user_id,))
                user_played_ids = {row["option_id"] for row in cur_user.fetchall()}
            except sqlite3.Error as e:
                print(f"Erreur lors de la lecture des paris : {e}")
                user_played_ids = set()

            # 3. Pour chaque match, récupérer ses options
            resultat = []
            for m in matchs:
                cur_opt = conn.execute(
                    "SELECT * FROM options WHERE match_id = ?", (m["id"],)
                )
                options = [dict(row) for row in cur_opt.fetchall()]

                # Ajouter l'info "joué par user" à chaque option
                for opt in options:
                    opt["user_played"] = opt["id"] in user_played_ids

                m["options"] = options
                resultat.append(m)

            return resultat

    except sqlite3.Error as e:
        print(f"Erreur historique : {e}")
        return []


def verifier_matchs_ouverts(liste_option_ids):
    """Vérifie si tous les matchs liés aux options fournies sont encore 'ouvert'."""
    if not liste_option_ids:
        return False

    try:
        with get_db_connection() as conn:
            placeholders = ",".join(["?"] * len(liste_option_ids))
            # On compte combien d'options pointent vers un match dont le statut n'est pas 'ouvert'
            sql = f"""
                SELECT COUNT(*) 
                FROM options o
                JOIN matchs m ON o.match_id = m.id
                WHERE o.id IN ({placeholders}) AND m.statut != 'ouvert'
            """
            cur = conn.execute(sql, liste_option_ids)
            matchs_fermes = cur.fetchone()[0]
            # Si le compte est 0, cela signifie que tout est 'ouvert'
            return matchs_fermes == 0
    except sqlite3.Error as e:
        print(f"Erreur vérification statut : {e}")
        return False
