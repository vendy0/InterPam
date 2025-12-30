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


def valider_option_gagnante(option_id, match_id):
    """
    Met l'option à 1 (gagné) et les autres options de la même
    catégorie pour ce match à 2 (perdu).
    """
    try:
        with get_db_connection() as conn:
            cur = conn.execute(
                "SELECT categorie FROM options WHERE id = ?", (option_id,)
            )
            res = cur.fetchone()
            if not res:
                return False
            categorie = res[0]

            # 2. Mettre toutes les options de cette catégorie pour ce match à 2 (perdu)
            conn.execute(
                """
                UPDATE options SET winner = 2 
                WHERE match_id = ? AND categorie = ?
            """,
                (match_id, categorie),
            )

            # 3. Mettre l'option spécifique à 1 (gagné)
            conn.execute("UPDATE options SET winner = 1 WHERE id = ?", (option_id,))

            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Erreur validation : {e}")
        return False


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


def fermer_match_officiellement(match_id):
    """Change le statut du match pour qu'il ne soit plus modifiable."""
    try:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE matchs SET statut = 'terminé' WHERE id = ?", (match_id,)
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Erreur fermeture match : {e}")
        return False


def executer_settlement_match(match_id):
    """
    Vérifie les paris liés au match et effectue le paiement si nécessaire.
    Version corrigée et sécurisée.
    """
    conn = None
    try:
        # On utilise le context manager pour la connexion, mais on gère le commit manuellement
        # pour s'assurer que tout ou rien n'est exécuté.
        conn = sqlite3.connect("interpam.db")
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
                cur.execute(
                    "UPDATE paris SET statut = 'Perdu' WHERE id = ?",
                    (p_id,),
                )
                stats["perdants"] += 1

            elif gagnees == total and total > 0:
                # Si TOUTES les options sont gagnantes (et qu'il y en a au moins une)
                # 1. Créditer le parieur
                cur.execute(
                    "UPDATE parieurs SET solde = solde + ? WHERE id = ?",
                    (gain_c, user_id),
                )
                # 2. Marquer le pari comme gagné
                cur.execute(
                    "UPDATE paris SET statut = 'Gagné' WHERE id = ? AND statut = 'En attente'", (p_id,)
                )
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


def get_bilan_financier_match(match_id):
    """Calcule le total des mises vs le total des gains payés pour un match."""
    try:
        with get_db_connection() as conn:
            # Somme des mises sur ce match
            cur = conn.execute(
                """
                SELECT SUM(p.mise) as total_mises
                FROM paris p
                JOIN matchs_paris mp ON p.id = mp.paris_id
                WHERE mp.matchs_id = ?
            """,
                (match_id,),
            )
            res_mises = cur.fetchone()

            # Somme des gains payés (uniquement pour les fiches marquées 'Gagné')
            cur = conn.execute(
                """
                SELECT SUM(p.gain_potentiel) as total_paye
                FROM paris p
                JOIN matchs_paris mp ON p.id = mp.paris_id
                WHERE mp.matchs_id = ? AND p.statut = 'Gagné'
            """,
                (match_id,),
            )
            res_gains = cur.fetchone()

            mises = res_mises["total_mises"] or 0
            gains = res_gains["total_paye"] or 0

            return {
                "mises": depuis_centimes(mises),
                "gains": depuis_centimes(gains),
                "benefice": depuis_centimes(mises - gains),
            }
    except sqlite3.Error as e:
        print(f"Erreur bilan : {e}")
        return None
