# # models/transaction.py
from database.connexion import get_db_connection
from utils.finance import depuis_centimes, vers_centimes
import sqlite3
from datetime import datetime
from models.emails import envoyer_push_notification
from models.config import mouvement_caisse
# # models/transaction.py


# def create_transaction(
#     user_id, type_trans, montant_dec, telephone, moncash_id=None, frais_dec=0, net_dec=0
# ):
#     try:
#         montant_centimes = vers_centimes(montant_dec)
#         frais_centimes = vers_centimes(frais_dec)

#         # Si c'est un dépôt, le net = le montant brut (pas de frais pour l'instant)
#         # Si c'est un retrait, net_dec est passé en argument
#         if net_dec == 0 and type_trans == "depot":
#             net_centimes = montant_centimes
#         else:
#             net_centimes = vers_centimes(net_dec)

#         created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#         with get_db_connection() as conn:
#             conn.execute(
#                 """INSERT INTO transactions
#                 (user_id, type, montant, frais, montant_net, telephone, moncash_id, created_at)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
#                 (
#                     user_id,
#                     type_trans,
#                     montant_centimes,
#                     frais_centimes,
#                     net_centimes,
#                     telephone,
#                     moncash_id,
#                     created_at,
#                 ),
#             )
#             conn.commit()
#             return True, "Demande enregistrée."
#     except sqlite3.IntegrityError:
#         return False, "Cet ID de transaction a déjà été utilisé."
#     except sqlite3.Error as e:
#         return False, f"Erreur base de données : {e}"


# # models/transaction.py


# def update_transaction_status(
#     tx_id, statut, admin_id, raison=None
# ):  # <-- Ajoute bien admin_id ici
#     """Met à jour le statut (valide/refuse) avec l'ID de l'admin."""
#     try:
#         processed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         with get_db_connection() as conn:
#             conn.execute(
#                 """UPDATE transactions
#                   SET statut = ?, processed_at = ?, admin_id = ?, raison_refus = ?
#                   WHERE id = ?""",
#                 (statut, processed_at, admin_id, raison, tx_id),
#             )
#             conn.commit()
#             return True
#     except sqlite3.Error as e:
#         print(f"Erreur update_transaction_status: {e}")
#         return False


# def _process_transaction_row(row):
#     """Helper pour formater les lignes de transaction"""
#     t = dict(row)
#     t["montant"] = depuis_centimes(t["montant"])  # Brut
#     # On gère le cas où les colonnes seraient nulles (anciennes transactions)
#     t["frais"] = depuis_centimes(t["frais"]) if t["frais"] else 0
#     t["montant_net"] = (
#         depuis_centimes(t["montant_net"]) if t["montant_net"] else t["montant"]
#     )
#     return t


# def transfert(
#     username_sender, username_getter, montant_dec, frais_dec, montant_net_dec
# ):
#     try:
#         montant_cent = vers_centimes(montant_dec)
#         frais_cent = vers_centimes(frais_dec)
#         montant_net_cent = vers_centimes(montant_net_dec)
#         created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#         with get_db_connection() as conn:
#             sender = conn.execute(
#                 "SELECT id, prenom FROM parieurs WHERE username = ?", (username_sender,)
#             ).fetchone()
#             getter = conn.execute(
#                 "SELECT id, push_subscription AS sub FROM parieurs WHERE username = ?",
#                 (username_getter,),
#             ).fetchone()
#             if not sender:
#                 print("Expéditeur introuvable !")
#                 return False
#             if not getter:
#                 print("Destinataire introuvable !")
#                 return False
#             conn.execute("BEGIN TRANSACTION")
#             cur = conn.execute(
#                 "UPDATE parieurs SET solde = solde - ? WHERE id = ?",
#                 (montant_cent, sender["id"]),
#             )
#             cur = conn.execute(
#                 "UPDATE parieurs SET solde = solde + ? WHERE id = ?",
#                 (montant_net_cent, getter["id"]),
#             )

#             cur = conn.execute(
#                 """INSERT INTO transactions(montant, frais, montant_net, processed_at, envoyeur_id, receveur_id) VALUES(?, ?, ?, ?, ?, ?)""",
#                 (
#                     montant_cent,
#                     frais_cent,
#                     montant_net_cent,
#                     created_at,
#                     sender["id"],
#                     getter["id"],
#                 ),
#             )
#             conn.execute("COMMIT TRANSACTION")
#             if getter["sub"]:
#                 envoyer_push_notification(
#                     getter["sub"],
#                     "Transfert reçu",
#                     f"Vous venez de recevoir un transfert de {depuis_centimes(montant_net_cent)} jetons de la part de {sender['prenom']}.",
#                 )
#             conn.commit()
#             mouvement_caisse(frais_dec, "add")
#             return True
#     except Exception as e:
#         print(f"Il y a eu une erreur lors du transfert : {e}")
#         conn.execute("ROLLBACK TRANSACTION")
#         return False


# def get_user_transactions(user_id):
#     try:
#         with get_db_connection() as conn:
#             cur = conn.execute(
#                 "SELECT * FROM transactions WHERE envoyeur_id = ? OR receveur_id = ? ORDER BY processed_at DESC",
#                 (
#                     user_id,
#                     user_id,
#                 ),
#             )
#             return [_process_transaction_row(r) for r in cur.fetchall()]
#     except sqlite3.Error as e:
#         print(f"Erreur: {e}")
#         return []


# def get_user_transactions(user_id):
#     try:
#         with get_db_connection() as conn:
#             cur = conn.execute(
#                 "SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC",
#                 (user_id,),
#             )
#             return [_process_transaction_row(r) for r in cur.fetchall()]
#     except sqlite3.Error as e:
#         print(f"Erreur: {e}")
#         return []


# def get_pending_transactions():
#     """Récupère toutes les transactions en attente pour l'admin avec infos user."""
#     try:
#         with get_db_connection() as conn:
#             query = """
#                 SELECT t.*, p.username, p.prenom, p.nom
#                 FROM transactions t
#                 JOIN parieurs p ON t.user_id = p.id
#                 WHERE t.statut = 'en_attente'
#                 ORDER BY t.created_at ASC
#             """
#             cur = conn.execute(query)
#             return [_process_transaction_row(r) for r in cur.fetchall()]
#     except sqlite3.Error as e:
#         print(f"Erreur get_pending_transactions: {e}")
#         return []


# def get_transaction_by_id(tx_id):
#     try:
#         with get_db_connection() as conn:
#             cur = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,))
#             res = cur.fetchone()
#             if res:
#                 t = dict(res)
#                 t["montant_dec"] = depuis_centimes(t["montant"])  # Helper
#                 return t
#             return None
#     except Exception as e:
#         return None


# def get_transaction_history():
#     """Récupère toutes les transactions traitées (validées/refusées)."""
#     try:
#         with get_db_connection() as conn:
#             query = """
#                 SELECT t.*, p.username, admin.prenom as admin_prenom, admin.nom as admin_nom
#                 FROM transactions t
#                 JOIN parieurs p ON t.user_id = p.id
#                 LEFT JOIN parieurs admin ON t.admin_id = admin.id
#                 WHERE t.statut != 'en_attente'
#                 ORDER BY t.processed_at DESC
#             """
#             cur = conn.execute(query)
#             return [_process_transaction_row(r) for r in cur.fetchall()]
#     except sqlite3.Error as e:
#         print(f"Erreur get_transaction_history: {e}")
#         return []

# models/transaction.py
# from database.connexion import get_db_connection
# from utils.finance import depuis_centimes, vers_centimes
# import sqlite3
# from datetime import datetime
# from models.emails import envoyer_push_notification
# from models.config import mouvement_caisse


def _process_transaction_row(row):
    """Helper pour formater les lignes (non utilisé dans la nouvelle logique globale, mais gardé au cas où)"""
    t = dict(row)
    t["montant"] = depuis_centimes(t["montant"])
    return t


def transfert(
    username_sender, username_getter, montant_dec, frais_dec, montant_net_dec
):
    """Gère le transfert P2P (inchangé, sauf imports)"""
    try:
        montant_cent = vers_centimes(montant_dec)
        frais_cent = vers_centimes(frais_dec)
        montant_net_cent = vers_centimes(montant_net_dec)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with get_db_connection() as conn:
            sender = conn.execute(
                "SELECT id, prenom FROM parieurs WHERE username = ?", (username_sender,)
            ).fetchone()
            getter = conn.execute(
                "SELECT id, push_subscription AS sub FROM parieurs WHERE username = ?",
                (username_getter,),
            ).fetchone()

            if not sender:
                return False
            if not getter:
                return False

            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "UPDATE parieurs SET solde = solde - ? WHERE id = ?",
                (montant_cent, sender["id"]),
            )
            conn.execute(
                "UPDATE parieurs SET solde = solde + ? WHERE id = ?",
                (montant_net_cent, getter["id"]),
            )

            conn.execute(
                """INSERT INTO transactions(montant, frais, montant_net, processed_at, envoyeur_id, receveur_id) 
                   VALUES(?, ?, ?, ?, ?, ?)""",
                (
                    montant_cent,
                    frais_cent,
                    montant_net_cent,
                    created_at,
                    sender["id"],
                    getter["id"],
                ),
            )
            conn.execute("COMMIT TRANSACTION")

            if getter["sub"]:
                envoyer_push_notification(
                    getter["sub"],
                    "Transfert reçu",
                    f"Vous avez reçu {depuis_centimes(montant_net_cent)} PMC de {sender['prenom']}.",
                )
            # Mise à jour de la caisse (frais gagnés)
            mouvement_caisse(frais_dec, "add")
            return True
    except Exception as e:
        print(f"Erreur transfert : {e}")
        return False


def get_user_transactions(user_id):
    """
    Récupère l'historique complet (Transferts P2P + Opérations Admin)
    et formate le tout pour l'affichage dans le wallet.
    """
    history = []

    try:
        with get_db_connection() as conn:
            # 1. Récupérer les Transferts (Envoyés et Reçus)
            # On joint pour avoir les noms des correspondants
            sql_trans = """
                SELECT t.*, 
                       s.username as sender_name, 
                       r.username as receiver_name 
                FROM transactions t
                LEFT JOIN parieurs s ON t.envoyeur_id = s.id
                LEFT JOIN parieurs r ON t.receveur_id = r.id
                WHERE t.envoyeur_id = ? OR t.receveur_id = ?
            """
            rows_trans = conn.execute(sql_trans, (user_id, user_id)).fetchall()

            for r in rows_trans:
                item = dict(r)
                item["source"] = "p2p"

                # Déterminer si c'est une entrée ou une sortie pour l'user actuel
                if item["envoyeur_id"] == user_id:
                    # J'ai envoyé de l'argent
                    item["type"] = "envoi"
                    item["display_montant"] = depuis_centimes(
                        item["montant"]
                    )  # Montant débité (Brut)
                    item["description"] = f"Envoyé à @{item['receiver_name']}"
                else:
                    # J'ai reçu de l'argent
                    item["type"] = "recu"
                    item["display_montant"] = depuis_centimes(
                        item["montant_net"]
                    )  # Montant reçu (Net)
                    item["description"] = f"Reçu de @{item['sender_name']}"

                # Standardiser la date pour le tri
                item["sort_date"] = item["processed_at"]
                history.append(item)

            # 2. Récupérer les Opérations Admin (Recharges / Retraits via Agent)
            sql_admin = """
                SELECT a.*, adm.prenom as admin_prenom
                FROM admin_transactions a
                LEFT JOIN parieurs adm ON a.admin_id = adm.id
                WHERE a.user_id = ?
            """
            rows_admin = conn.execute(sql_admin, (user_id,)).fetchall()

            for r in rows_admin:
                item = dict(r)
                item["source"] = r["admin_prenom"]
                item["display_montant"] = depuis_centimes(item["montant"])
                item["sort_date"] = item["created_at"]

                # Mapping des types admin vers affichage
                if item["type"] == "credit":
                    item["type"] = "depot"
                    item["description"] = f"Recharge (Agent {item['admin_prenom']})"
                elif item["type"] == "debit":
                    item["type"] = "retrait"
                    item["description"] = f"Retrait (Agent {item['admin_prenom']})"

                history.append(item)

    except sqlite3.Error as e:
        print(f"Erreur historique : {e}")
        return []

    # 3. Trier par date décroissante (le plus récent en haut)
    history.sort(key=lambda x: x["sort_date"], reverse=True)

    return history
