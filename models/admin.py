from database.connexion import get_db_connection
from utils.finance import vers_centimes, depuis_centimes
import sqlite3
import smtplib
from email.message import EmailMessage
from models.emails import *
from flask import url_for


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
            cur = conn.execute(
                "SELECT push_subscription AS sub FROM parieurs WHERE push_subscription IS NOT NULL"
            )
            users = cur.fetchall()
            cur = conn.execute("SELECT * FROM matchs WHERE id = ?", (match_id,))
            match = cur.fetchone()
            for user in users:
                message = (
                    f"Le match {match['equipe_a']} VS {match['equipe_b']} est terminé !"
                )
                envoyer_push_notification(user["sub"], "Match terminé", message)
            conn.commit()
            return True
    except Exception as e:
        print(f"Erreur fermeture match : {e}")
        return False


def executer_settlement_match(match_id):
    """
    Vérifie les paris liés au match et effectue le paiement si nécessaire.
    """
    conn = None
    try:
        conn = sqlite3.connect("interpam.db")
        # Permet d'accéder aux colonnes par nom : row['solde'] au lieu de row[1]
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1. Récupérer tous les paris "En attente" contenant ce match
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
        stats = {"gagnants": 0, "perdants": 0}

        if not paris_a_verifier:
            conn.close()
            return True, "Aucun pari en attente pour ce match."

        for pari in paris_a_verifier:
            p_id = pari["id"]
            u_id = pari["parieur_id"]
            gain_c = pari["gain_potentiel"]

            # 2. Vérifier l'état global du ticket
            cur.execute(
                """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN o.winner = 2 THEN 1 ELSE 0 END) as perdues,
                    SUM(CASE WHEN o.winner = 1 THEN 1 ELSE 0 END) as gagnees
                FROM matchs_paris mp
                JOIN options o ON mp.option_id = o.id
                WHERE mp.paris_id = ?
            """,
                (p_id,),
            )

            res = cur.fetchone()
            total, perdues, gagnees = (
                res["total"],
                res["perdues"] or 0,
                res["gagnees"] or 0,
            )

            # --- LOGIQUE DE DÉCISION ---

            if perdues > 0:
                # Échec : Au moins un match du combiné est faux
                cur.execute("UPDATE paris SET statut = 'Perdu' WHERE id = ?", (p_id,))
                stats["perdants"] += 1

            elif gagnees == total:
                # Succès : Tous les matchs du ticket sont gagnés
                # 1. Créditer le solde du parieur (Atomic update)
                cur.execute(
                    "UPDATE parieurs SET solde = solde + ? WHERE id = ?", (gain_c, u_id)
                )
                # 2. Marquer le ticket comme gagné
                cur.execute("UPDATE paris SET statut = 'Gagné' WHERE id = ?", (p_id,))
                stats["gagnants"] += 1

                # 3. Notification (Optionnel mais recommandé)
                envoi_notification_gain(cur, u_id, gain_c)

        conn.commit()
        return (
            True,
            f"Settlement réussi : {stats['gagnants']} gagnés, {stats['perdants']} perdus.",
        )

    except Exception as e:
        if conn:
            conn.rollback()
        return False, f"Erreur settlement : {str(e)}"
    finally:
        if conn:
            conn.close()


def envoi_notification_gain(cursor, user_id, gain_c):
    """Sous-fonction pour gérer les notifications sans casser la boucle principale"""
    cursor.execute(
        "SELECT push_subscription, solde FROM parieurs WHERE id = ?", (user_id,)
    )
    user = cursor.fetchone()
    if user and user["push_subscription"]:
        try:
            message = f"Félicitations ! Gain de {depuis_centimes(gain_c)} HTG reçu."
            envoyer_push_notification(
                user["push_subscription"], "Pari Gagné !", message
            )
        except:
            pass  # Ne pas bloquer le paiement si la notification échoue


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
            closed = conn.execute(
                "SELECT * FROM matchs WHERE id = ? AND statut <> 'fermé'", (match_id,)
            )
            match = closed.fetchone()
            cur = conn.execute(
                """
                UPDATE matchs 
                SET equipe_a = ?, equipe_b = ?, date_match = ?, statut = ?, type_match = ?
                WHERE id = ?
                """,
                (equipe_a, equipe_b, date_match, statut, type_match, match_id),
            )
            if match:
                cur = conn.execute(
                    "SELECT push_subscription AS sub FROM parieurs WHERE push_subscription IS NOT NULL"
                )
                users = cur.fetchall()
                for user in users:
                    message = f"Le match {match['equipe_a']} VS {match['equipe_b']} vient d'être fermé à tous nouveaux paris !"
                    envoyer_push_notification(user["sub"], "Match terminé", message)
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


def ban_ret_user(username, message, ban=False, ret=False):
    try:
        with get_db_connection() as conn:
            cur = conn.execute(
                "SELECT push_subscription AS sub, prenom, email FROM parieurs WHERE username = ?",
                (username,),
            )
            user = cur.fetchone()
            if not user:
                return False

            if ban == True:
                conn.execute(
                    "UPDATE parieurs SET actif = 0 WHERE username = ?", (username,)
                )
                conn.commit()

                # Notifications

                if user["sub"]:
                    message_else = "Votre compte vient d'être suspendu !"
                    message_ban = message if message else message_else
                    envoyer_push_notification(
                        user["sub"],
                        "Compte suspendu",
                        message_ban,
                        url=url_for("index", _external=True),
                    )

                ban_notification(user["prenom"], user["email"])
                return True
            elif ret == True:
                conn.execute(
                    "UPDATE parieurs SET actif = 1 WHERE username = ?", (username,)
                )
                conn.commit()
                if user["sub"]:
                    message_else = "Félicitations, votre compte InterPam a été restauré. Vous pouvez désormais vous connecter !"
                    message_ret = message if message else message_else
                    envoyer_push_notification(
                        user["sub"], "Compte rétabli", message_ret
                    )
                ret_notification(user["prenom"], user["email"])
                return True
            else:
                return False
    except sqlite3.Error as e:
        print(f"Erreur lors du bannissement / rétablissement : {e}")
        return False
