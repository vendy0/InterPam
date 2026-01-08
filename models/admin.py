from database.connexion import get_db_connection
from utils.finance import vers_centimes, depuis_centimes
import sqlite3
import smtplib
from email.message import EmailMessage
from models.emails import *
from flask import url_for


def get_dashboard_stats():
    """Récupère les statistiques globales pour le dashboard."""
    stats = {
        "mises_totales": 0,
        "gains_distribues": 0,
        "benefice": 0,
        "total_joueurs": 0,
        "joueurs_bannis": 0,
    }

    try:
        with get_db_connection() as conn:
            # 1. Statistiques Financières (Table paris)
            query_finance = """
				SELECT 
					SUM(mise) as total_mises,
					SUM(CASE WHEN statut = 'Gagné' THEN gain_potentiel ELSE 0 END) as total_gains
				FROM paris
			"""
            cur = conn.execute(query_finance)
            res_finance = cur.fetchone()

            mises = res_finance["total_mises"] if res_finance["total_mises"] else 0
            gains = res_finance["total_gains"] if res_finance["total_gains"] else 0

            # 2. Statistiques Joueurs (Table parieurs)
            query_users = """
				SELECT 
					COUNT(*) as total,
					SUM(CASE WHEN actif = 0 THEN 1 ELSE 0 END) as bannis
				FROM parieurs
				WHERE classe != Direction
			"""
            cur = conn.execute(query_users)
            res_users = cur.fetchone()

            # Formatage des données
            stats["mises_totales"] = depuis_centimes(mises)
            stats["gains_distribues"] = depuis_centimes(gains)
            stats["benefice"] = depuis_centimes(mises - gains)
            stats["total_joueurs"] = res_users["total"]
            stats["joueurs_bannis"] = res_users["bannis"] if res_users["bannis"] else 0

            return stats
    except Exception as e:
        print(f"Erreur stats dashboard: {e}")
        return stats


def valider_option_gagnante(option_id, match_id):
    """Met l'option à 1 (gagné) et les autres de la même catégorie à 2 (perdu)."""
    try:
        with get_db_connection() as conn:
            cur = conn.execute(
                "SELECT categorie FROM options WHERE id = ?", (option_id,)
            )
            res = cur.fetchone()
            if not res:
                return False
            categorie = res[0]

            conn.execute(
                "UPDATE options SET winner = 2 WHERE match_id = ? AND categorie = ?",
                (match_id, categorie),
            )
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
                try:
                    message = f"Le match {match['equipe_a']} VS {match['equipe_b']} est terminé !"
                    envoyer_push_notification(user["sub"], "Match terminé", message)
                except Exception as e:
                    print(f"Échec notification : {e}")
            conn.commit()
            return True
    except Exception as e:
        print(f"Erreur fermeture match : {e}")
        return False


def update_match_info(match_id, equipe_a, equipe_b, date_match, statut, type_match):
    """Met à jour les informations du match avec notifications intelligentes."""
    try:
        with get_db_connection() as conn:
            # 1. Récupérer l'état actuel avant modification
            cur = conn.execute("SELECT * FROM matchs WHERE id = ?", (match_id,))
            old = cur.fetchone()
            if not old:
                return False

            # 2. Déterminer le type de message
            # Vérifier si des données structurelles ont changé
            data_changed = (
                old["equipe_a"] != equipe_a
                or old["equipe_b"] != equipe_b
                or old["date_match"] != date_match
                or old["type_match"] != type_match
            )

            status_changed = old["statut"] != statut

            notification_title = "Mise à jour Match"
            if data_changed:
                notification_msg = f"Le match {equipe_a} VS {equipe_b} a été modifié."
            elif status_changed:
                if old["statut"] == "ouvert" and statut == "fermé":
                    notification_msg = f"Le match {equipe_a} VS {equipe_b} est désormais fermé aux paris."
                elif old["statut"] == "fermé" and statut == "ouvert":
                    notification_msg = (
                        f"Le match {equipe_a} VS {equipe_b} est de nouveau ouvert !"
                    )
                else:
                    notification_msg = f"Le statut du match {equipe_a} VS {equipe_b} est passé à : {statut}."
            else:
                notification_msg = None  # Rien n'a changé

            # 3. Appliquer la mise à jour
            conn.execute(
                """
				UPDATE matchs 
				SET equipe_a = ?, equipe_b = ?, date_match = ?, statut = ?, type_match = ?
				WHERE id = ?
			""",
                (equipe_a, equipe_b, date_match, statut, type_match, match_id),
            )

            # 4. Envoyer les notifications si nécessaire
            if notification_msg:
                cur = conn.execute(
                    "SELECT push_subscription AS sub FROM parieurs WHERE push_subscription IS NOT NULL"
                )
                users = cur.fetchall()
                for user in users:
                    try:
                        envoyer_push_notification(
                            user["sub"], notification_title, notification_msg
                        )
                    except:
                        continue

            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Erreur update_match_info : {e}")
        return False


def get_bilan_financier_match(match_id):
    """Calcule le total des mises vs le total des gains payés pour un match."""
    try:
        with get_db_connection() as conn:
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


def envoi_notification_gain(cursor, user_id, gain_c):
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
            pass


def ajouter_match(equipe_a, equipe_b, date_match, type_match):
    try:
        with get_db_connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cur = conn.execute(
                "INSERT INTO matchs (equipe_a, equipe_b, date_match, type_match) VALUES (?, ?, ?, ?)",
                (equipe_a, equipe_b, date_match, type_match),
            )
            return cur.lastrowid
    except sqlite3.Error as e:
        print(f"Erreur ajout match : {e}")


def ajouter_option(libelle, cote, categorie, match_id):
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO options(libelle, cote, categorie, match_id) VALUES (?, ?, ?, ?)",
                (libelle, cote, categorie, match_id),
            )
    except sqlite3.Error as e:
        print(f"Erreur ajout option : {e}")


def update_option_info(option_id, libelle, cote, categorie):
    try:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE options SET libelle = ?, cote = ?, categorie = ? WHERE id = ?",
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
        print(f"Erreur suppression : {e}")
        return False


def annuler_match_et_rembourser(match_id):
    try:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE matchs SET statut = 'annulé' WHERE id = ?", (match_id,)
            )
            cur = conn.execute(
                "SELECT id, cote FROM options WHERE match_id = ?", (match_id,)
            )
            options_du_match = cur.fetchall()
            conn.execute(
                "UPDATE options SET winner = 3 WHERE match_id = ?", (match_id,)
            )

            for option in options_du_match:
                opt_id = option["id"]
                cote_annulee = option["cote"]
                sql_paris = """
					SELECT p.id, p.gain_potentiel 
					FROM paris p
					JOIN matchs_paris mp ON p.id = mp.paris_id
					WHERE mp.option_id = ? AND p.statut = 'En attente'
				"""
                cur_p = conn.execute(sql_paris, (opt_id,))
                for pari in cur_p.fetchall():
                    nouveau_gain = (
                        int(pari["gain_potentiel"] / cote_annulee)
                        if cote_annulee > 1
                        else pari["gain_potentiel"]
                    )
                    conn.execute(
                        "UPDATE paris SET gain_potentiel = ? WHERE id = ?",
                        (nouveau_gain, pari["id"]),
                    )

            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Erreur annulation : {e}")
        return False


def executer_settlement_match(match_id):
    conn = None
    try:
        conn = sqlite3.connect("interpam.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
			SELECT DISTINCT p.id, p.parieur_id, p.gain_potentiel, p.mise
			FROM paris p
			JOIN matchs_paris mp ON p.id = mp.paris_id
			WHERE mp.matchs_id = ? AND p.statut = 'En attente'
		""",
            (match_id,),
        )

        paris_a_verifier = cur.fetchall()
        stats = {"gagnants": 0, "perdants": 0, "annules": 0}

        for pari in paris_a_verifier:
            cur.execute(
                """
				SELECT 
					COUNT(*) as total,
					SUM(CASE WHEN o.winner = 2 THEN 1 ELSE 0 END) as perdus,
					SUM(CASE WHEN o.winner = 1 THEN 1 ELSE 0 END) as gagne_stricts,
					SUM(CASE WHEN o.winner = 3 THEN 1 ELSE 0 END) as annulés
				FROM matchs_paris mp
				JOIN options o ON mp.option_id = o.id
				WHERE mp.paris_id = ?
			""",
                (pari["id"],),
            )
            res = cur.fetchone()

            if (res["perdus"] or 0) > 0:
                cur.execute(
                    "UPDATE paris SET statut = 'Perdu' WHERE id = ?", (pari["id"],)
                )
                stats["perdants"] += 1
            elif (res["annulés"] or 0) == res["total"]:
                cur.execute(
                    "UPDATE paris SET statut = 'Annulé' WHERE id = ?", (pari["id"],)
                )
                cur.execute(
                    "UPDATE parieurs SET solde = solde + ? WHERE id = ?",
                    (pari["gain_potentiel"], pari["parieur_id"]),
                )
                stats["annules"] += 1
            elif ((res["gagne_stricts"] or 0) + (res["annulés"] or 0)) == res["total"]:
                cur.execute(
                    "UPDATE paris SET statut = 'Gagné' WHERE id = ?", (pari["id"],)
                )
                cur.execute(
                    "UPDATE parieurs SET solde = solde + ? WHERE id = ?",
                    (pari["gain_potentiel"], pari["parieur_id"]),
                )
                stats["gagnants"] += 1
                envoi_notification_gain(cur, pari["parieur_id"], pari["gain_potentiel"])

        conn.commit()
        return True, "Settlement terminé"
    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e)
    finally:
        if conn:
            conn.close()


def creer_invitation_admin(email, role, token, expiration):
    try:
        with get_db_connection() as conn:
            cur = conn.execute("SELECT * FROM parieurs WHERE email = ?", (email,))
            if cur.fetchone():
                return False, "Cet email est déjà utilisé !"
            conn.execute(
                "INSERT INTO invitations (email, role, token, expiration) VALUES (?, ?, ?, ?)",
                (email, role, token, expiration),
            )
            conn.commit()
            return True, "Invitation créée !"
    except sqlite3.Error as e:
        return False, str(e)


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

            if ban:
                conn.execute(
                    "UPDATE parieurs SET actif = 0 WHERE username = ?", (username,)
                )
                if user["sub"]:
                    envoyer_push_notification(
                        user["sub"],
                        "Compte suspendu",
                        message or "Votre compte est suspendu.",
                    )
                ban_notification(user["prenom"], user["email"])
            elif ret:
                conn.execute(
                    "UPDATE parieurs SET actif = 1 WHERE username = ?", (username,)
                )
                if user["sub"]:
                    envoyer_push_notification(
                        user["sub"], "Compte rétabli", "Votre compte a été restauré."
                    )
                ret_notification(user["prenom"], user["email"])
            conn.commit()
            return True
    except sqlite3.Error:
        return False


def get_messages():
    try:
        with get_db_connection() as conn:
            query = "SELECT m.*, p.prenom, p.nom FROM messagerie m LEFT JOIN parieurs p ON m.parieur_id = p.id ORDER BY m.created_at DESC"
            return conn.execute(query).fetchall()
    except sqlite3.Error:
        return []


def mark_as_read(message_id):
    try:
        with get_db_connection() as conn:
            cur = conn.execute(
                "SELECT read FROM messagerie WHERE id = ?", (message_id,)
            )
            msg = cur.fetchone()
            if not msg:
                return False
            new_status = 1 if msg["read"] == 0 else 0
            conn.execute(
                "UPDATE messagerie SET read = ? WHERE id = ?", (new_status, message_id)
            )
            conn.commit()
            return True
    except sqlite3.Error:
        return False
