from database.connexion import get_db_connection
import sqlite3
from models.emails import envoyer_push_notification

def ajouter_match(equipe_a, equipe_b, date_match, type_match="foot"):
    try:
        with get_db_connection() as conn:
            cur = conn.execute(
                "INSERT INTO matchs (equipe_a, equipe_b, date_match, statut, type_match) VALUES (?, ?, ?, 'ouvert', ?)",
                (equipe_a, equipe_b, date_match, type_match),
            )
            cur = conn.execute(
                "SELECT push_subscription AS sub FROM parieurs WHERE push_subscription IS NOT NULL"
            )
            users = cur.fetchall()
            for user in users:
                message = f"Le match {equipe_a} VS {equipe_b} vient d'être ajouté. Cliquez ici pour commencer à parier dès maintenant !"
                envoyer_push_notification(user["sub"], "Match ajouté", message)
                conn.commit()
            return cur.lastrowid
    except sqlite3.Error as e:
        print(f"Erreur lors de l'ajout du match : {e}")


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
                WHERE statut != 'terminé'
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
