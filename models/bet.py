from database.connexion import get_db_connection
from utils.finance import vers_centimes, depuis_centimes
import sqlite3


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

        with get_db_connection() as conn:
            conn.execute("BEGIN TRANSACTION")

            # --- Vérification solde ---
            cur = conn.execute("SELECT solde FROM parieurs WHERE id = ?", (parieur_id,))
            row = cur.fetchone()
            if not row:
                return False, "Parieur introuvable"

            solde_c = row[0]
            if solde_c < mise_c:
                return False, "Solde insuffisant"

            # --- Débit du solde ---
            conn.execute(
                "UPDATE parieurs SET solde = solde - ? WHERE id = ?",
                (mise_c, parieur_id),
            )

            # --- Création du pari ---
            cur = conn.execute(
                """
                INSERT INTO paris (mise, gain_potentiel, date_pari, parieur_id)
                VALUES (?, ?, ?, ?)
                """,
                (mise_c, gain_c, date_pari, parieur_id),
            )
            pari_id = cur.lastrowid

            # --- Liaison options ---
            for opt_id in options_ids:
                conn.execute(
                    "INSERT INTO matchs_paris (paris_id, matchs_id, option_id) VALUES (?, ?, ?)",
                    (pari_id, match_id, opt_id),
                )

            conn.commit()
            return True, "Pari placé avec succès"

    except Exception as e:
        return False, f"Erreur lors du pari : {e}"


def obtenir_cotes_par_ids(liste_ids):
    """Retourne la liste des cotes pour les IDs fournis."""
    if not liste_ids:
        return []

    try:
        with get_db_connection() as conn:
            placeholders = ",".join(["?"] * len(liste_ids))
            requete = f"SELECT cote FROM options WHERE id IN ({placeholders})"
            conn.execute(requete, liste_ids)
            resultats = conn.fetchall()
            return [r[0] for r in resultats]
    except sqlite3.Error as e:
        print(f"Erreur SQL : {e}")
        return []



def get_fiches_detaillees(parieur_id):
    try:
        with get_db_connection() as conn:
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
            cur = conn.execute(query, (parieur_id,))
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


def get_details_options_panier(liste_option_ids):
    """Récupère les détails complets pour l'affichage du panier"""
    if not liste_option_ids:
        return []

    try:
        with get_db_connection() as conn:
            # On formate les ? pour le nombre d'IDs
            placeholders = ",".join(["?"] * len(liste_option_ids))
            sql = f"""
                SELECT o.id as option_id, o.libelle, o.cote, o.categorie,
                       m.id as match_id, m.equipe_a, m.equipe_b, m.date_match
                FROM options o
                JOIN matchs m ON o.match_id = m.id
                WHERE o.id IN ({placeholders})
            """
            cur = conn.execute(sql, liste_option_ids)
            return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Erreur panier : {e}")
        return []


