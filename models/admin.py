from database.connexion import get_db_connection
from utils.finance import vers_centimes, depuis_centimes
import sqlite3


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
                    "UPDATE paris SET statut = 'Gagné' WHERE id = ? AND statut = 'En attente'",
                    (p_id,),
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


def ajouter_option(libelle, cote, categorie, match_id):
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO options(libelle, cote, categorie, match_id) VALUES (?, ?, ?, ?)",
                (libelle, cote, categorie, match_id),
            )
            print(
                f"Option {libelle} x {cote} de la catégorie {categorie} créé avec succès."
            )
    except sqlite3.Error as e:
        print(f"Erreur lors de l'ajout : {e}")


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


def supprimer_match(match_id):
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM matchs WHERE id = ?", (match_id,))
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Il y a eu une erreur lors de la suppression : {e}")
        return False


"""
---------------------------------------
STAFF
---------------------------------------
"""


def creer_invitation_admin(email, role, token, expiration):
    try:
        with get_db_connection() as conn:
            cur = conn.execute("SELECT * FROM parieurs WHERE email = ?", (email,))
            yet = cur.fetchone()
            if yet:
                return False, "Cet email est déja utilisé !"
            conn.execute(
                "INSERT INTO invitations (email, role, token, expiration) VALUES (?, ?, ?, ?)",
                (
                    email,
                    role,
                    token,
                    expiration,
                ),
            )
            conn.commit()
            return True, "Invitation créée avec succès !"
    except sqlite3.Error as e:
        print(f"Il y a eu une erreur lors de l'ajout se l'invitation : {e}")
        return False, f"Il y a eu une erreur lors de l'ajout se l'invitation : {e}"


def get_invitation_by_token(token):
    try:
        with get_db_connection() as conn:
            cur = conn.execute("SELECT * FROM invitations WHERE token = ?", (token,))
            res = cur.fetchone()
            return res
    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération des invitations : {e}")


def supprimer_invitation(token):
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM invitations WHERE token = ?", (token,))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Erreur lors de la suppression de l'invitation {e}")
