from database.connexion import get_db_connection
import sqlite3


def ajouter_match(equipe_a, equipe_b, date_match, type_match="foot"):
    with get_db_connection() as conn:
        cur = conn.execute(
            "INSERT INTO matchs (equipe_a, equipe_b, date_match, statut, type_match) VALUES (?, ?, ?, 'ouvert', ?)",
            (equipe_a, equipe_b, date_match, type_match),
        )
        conn.commit()
        return cur.lastrowid


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
    """Récupère les matchs ouverts avec leurs options"""
    with get_db_connection() as conn:
        # On récupère les matchs
        matchs = conn.execute("SELECT * FROM matchs WHERE statut = 'ouvert'").fetchall()
        programmes = []
        for m in matchs:
            m_dict = dict(m)
            opts = conn.execute(
                "SELECT * FROM options_match WHERE match_id = ?", (m_dict["id"],)
            ).fetchall()
            m_dict["options"] = [dict(o) for o in opts]
            programmes.append(m_dict)
        return programmes


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


def update_match_info(match_id, equipe_a, equipe_b, date_match, statut, type_match):
    """Met à jour les informations générales du match."""
    try:
        with get_db_connection() as conn:
            cur = conn.execute(
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
        with get_db_connection() as conn:
            cur = conn.execute(
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
