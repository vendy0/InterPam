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
            # On somme toutes les mises, et on somme les gains seulement si le pari est 'Gagné'
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
            # actif = 0 signifie banni/inactif selon ton schéma
            query_users = """
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN actif = 0 THEN 1 ELSE 0 END) as bannis
                FROM parieurs
                WHERE role != 'admin' AND role != 'super_admin'
            """
            cur = conn.execute(query_users)
            res_users = cur.fetchone()

            # Formatage des données
            stats["mises_totales"] = depuis_centimes(mises)
            stats["gains_distribues"] = depuis_centimes(gains)
            stats["benefice"] = depuis_centimes(
                mises - gains
            )  # Bénéfice net pour InterPam
            stats["total_joueurs"] = res_users["total"]
            stats["joueurs_bannis"] = res_users["bannis"] if res_users["bannis"] else 0

            return stats

    except Exception as e:
        print(f"Erreur stats dashboard: {e}")
        return stats


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


def ajouter_match(equipe_a, equipe_b, date_match, type_match):
    """Ajoute un match."""
    try:
        with get_db_connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cur = conn.execute(
                "INSERT INTO matchs (equipe_a, equipe_b, date_match, type_match) VALUES (?, ?, ?, ?)",
                (equipe_a, equipe_b, date_match, type_match),
            )
            id_match = cur.lastrowid
            print(
                f"Match ajouté avec succès : {equipe_a} VS {equipe_b}, id : {id_match}"
            )
            return id_match
    except sqlite3.Error as e:
        print(f"Erreur lors de l'ajout du match : {e}")


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


def annuler_match_et_rembourser(match_id):
    """
    Annule un match :
    1. Change le statut du match en 'annulé'
    2. Change le status des options en 3 (Code pour Annulé/Void)
    3. Recalcule le gain potentiel de tous les tickets affectés (Division par la cote)
    """
    try:
        with get_db_connection() as conn:
            # 1. Update Match Statut
            conn.execute(
                "UPDATE matchs SET statut = 'annulé' WHERE id = ?", (match_id,)
            )

            # 2. Récupérer les options avant de les modifier pour avoir les cotes
            cur = conn.execute(
                "SELECT id, cote FROM options WHERE match_id = ?", (match_id,)
            )
            options_du_match = cur.fetchall()

            # 3. Mettre les options à winner = 3 (Annulé)
            conn.execute(
                "UPDATE options SET winner = 3 WHERE match_id = ?", (match_id,)
            )

            # 4. RECALCUL DES PARIS (La partie importante)
            print(f"--- Début traitement annulation match {match_id} ---")

            for option in options_du_match:
                opt_id = option["id"]
                cote_annulee = option["cote"]

                # Trouver tous les paris 'En attente' qui contiennent cette option
                sql_paris = """
                    SELECT p.id, p.gain_potentiel 
                    FROM paris p
                    JOIN matchs_paris mp ON p.id = mp.paris_id
                    WHERE mp.option_id = ? AND p.statut = 'En attente'
                """
                cur_p = conn.execute(sql_paris, (opt_id,))
                paris_affectes = cur_p.fetchall()

                for pari in paris_affectes:
                    pari_id = pari["id"]
                    ancien_gain = pari["gain_potentiel"]

                    # Formule : Nouveau Gain = Ancien Gain / Cote Annulée
                    # Attention : on travaille en centimes (entiers), donc division entière
                    # Mais pour la précision, on repasse par le calcul mathématique

                    if cote_annulee > 1:
                        nouveau_gain = int(ancien_gain / cote_annulee)
                    else:
                        nouveau_gain = ancien_gain  # Sécurité division par 0 ou 1

                    # Mise à jour du gain potentiel
                    conn.execute(
                        "UPDATE paris SET gain_potentiel = ? WHERE id = ?",
                        (nouveau_gain, pari_id),
                    )
                    print(f"Pari #{pari_id} ajusté : {ancien_gain} -> {nouveau_gain}")
            conn.commit()
            cur = conn.execute(
                "SELECT push_subscription as sub FROM parieurs WHERE push_subscription IS NOT NULL"
            )
            users = cur.fetchall()
            if users:
                for user in users:
                    cur = conn.execute(
                        "SELECT equipe_a, equipe_b FROM matchs WHERE id = ?",
                        (match_id,),
                    )
                    match = cur.fetchone()
                    envoyer_push_notification(
                        user["sub"],
                        "Match annulé",
                        f"Le match {match['equipe_a']} VS {match['equipe_b']} vient d'être annulé.",
                    )

            # 5. Envoyer une notif aux joueurs concernés (Optionnel mais sympa)
            # ... (code notification ici si tu veux)

            return True

    except sqlite3.Error as e:
        print(f"Erreur lors de l'annulation du match : {e}")
        return False


# IL FAUT AUSSI MODIFIER 'executer_settlement_match' pour qu'il comprenne le code 3
# Remplace ta fonction executer_settlement_match existante par celle-ci corrigée :
def executer_settlement_match(match_id):
    """
    Vérifie les paris liés au match et effectue le paiement si nécessaire.
    Gère strictement les statuts : Perdu > Annulé > Gagné > En attente.
    """
    conn = None
    try:
        conn = sqlite3.connect("interpam.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1. Récupérer tous les paris "En attente" qui contiennent ce match
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

        if not paris_a_verifier:
            conn.close()
            return True, "Aucun pari en attente affecté."

        print(f"--- Settlement : Vérification de {len(paris_a_verifier)} tickets ---")

        for pari in paris_a_verifier:
            p_id = pari["id"]
            u_id = pari["parieur_id"]
            gain_c = pari["gain_potentiel"]
            mise_c = pari["mise"]

            # 2. Compter les statuts des options du ticket
            # winner : 0=En cours, 1=Gagné, 2=Perdu, 3=Annulé
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
                (p_id,),
            )

            res = cur.fetchone()
            total = res["total"]
            perdus = res["perdus"] or 0
            gagne_stricts = res["gagne_stricts"] or 0
            annules = res["annulés"] or 0

            # --- LOGIQUE DE DÉCISION STRICTE ---

            # CAS 1 : Au moins une option perdante -> Ticket PERDU
            if perdus > 0:
                cur.execute("UPDATE paris SET statut = 'Perdu' WHERE id = ?", (p_id,))
                stats["perdants"] += 1

            # CAS 2 : Toutes les options sont annulées -> Ticket ANNULÉ (Remboursement)
            elif annules == total:
                cur.execute("UPDATE paris SET statut = 'Annulé' WHERE id = ?", (p_id,))
                # On rembourse la mise (ou le gain recalculé qui devrait être égal à la mise)
                # Note: annuler_match_et_rembourser a déjà ajusté gain_potentiel vers la mise normalement
                cur.execute(
                    "UPDATE parieurs SET solde = solde + ? WHERE id = ?", (gain_c, u_id)
                )
                stats["annules"] += 1
                print(f"Ticket #{p_id} -> ANNULÉ (Remboursé)")

            # CAS 3 : Le ticket est complet (Gagnés + Annulés = Total) -> Ticket GAGNÉ
            # Cela signifie qu'il n'y a pas de perdants, pas d'attente, et ce n'est pas 100% annulé
            elif (gagne_stricts + annules) == total:
                cur.execute("UPDATE paris SET statut = 'Gagné' WHERE id = ?", (p_id,))
                cur.execute(
                    "UPDATE parieurs SET solde = solde + ? WHERE id = ?", (gain_c, u_id)
                )
                stats["gagnants"] += 1
                envoi_notification_gain(cur, u_id, gain_c)

            # CAS 4 : Il reste des matchs en attente (winner = 0) -> On ne fait rien
            else:
                pass

        conn.commit()
        return (
            True,
            f"Settlement réussi : {stats['gagnants']} gagnés, {stats['perdants']} perdus, {stats['annules']} annulés.",
        )

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"ERREUR SETTLEMENT: {e}")
        return False, f"Erreur settlement : {str(e)}"
    finally:
        if conn:
            conn.close()


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


def get_messages():
    try:
        with get_db_connection() as conn:
            # On sélectionne les colonnes du message ET les colonnes de l'utilisateur
            query = """
                SELECT m.*, p.prenom, p.nom 
                FROM messagerie m
                LEFT JOIN parieurs p ON m.parieur_id = p.id
                ORDER BY m.created_at DESC
            """
            cur = conn.execute(query)
            # fetchall() renvoie des objets sqlite3.Row qui se comportent comme des dicts
            return cur.fetchall()
    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération : {e}")
        return []


def mark_as_read(message_id):
    try:
        with get_db_connection() as conn:
            cur = conn.execute(
                "SELECT read FROM messagerie WHERE id = ?", (message_id,)
            )
            message = cur.fetchone()
            if not message:
                return False
            if message["read"] == 0:
                cur = conn.execute(
                    "UPDATE messagerie SET read = 1 WHERE id = ?", (message_id,)
                )
            else:
                cur = conn.execute(
                    "UPDATE messagerie SET read = 0 WHERE id = ?", (message_id,)
                )
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Erreur lors du marquage : {e}")
        return False
