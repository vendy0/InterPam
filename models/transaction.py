from database.connexion import get_db_connection
from utils.finance import depuis_centimes, vers_centimes
import sqlite3
from datetime import datetime
from models.emails import envoyer_push_notification
from models.config import mouvement_caisse

def transfert(
    username_sender, username_getter, montant_dec, frais_dec, montant_net_dec
):
    """Gère le transfert P2P instantané"""
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

            if not sender: return False
            if not getter: return False

            conn.execute("BEGIN TRANSACTION")
            conn.execute("UPDATE parieurs SET solde = solde - ? WHERE id = ?", (montant_cent, sender["id"]))
            conn.execute("UPDATE parieurs SET solde = solde + ? WHERE id = ?", (montant_net_cent, getter["id"]))

            # Note: La table transactions (nouvelle version) n'a plus de colonne 'statut'
            conn.execute(
                """INSERT INTO transactions(montant, frais, montant_net, processed_at, envoyeur_id, receveur_id) 
                   VALUES(?, ?, ?, ?, ?, ?)""",
                (montant_cent, frais_cent, montant_net_cent, created_at, sender["id"], getter["id"]),
            )
            conn.execute("COMMIT TRANSACTION")

            if getter["sub"]:
                envoyer_push_notification(
                    getter["sub"],
                    "Transfert reçu",
                    f"Vous avez reçu {depuis_centimes(montant_net_cent)} PMC de {sender['prenom']}.",
                )
            mouvement_caisse(frais_dec, "add")
            return True
    except Exception as e:
        print(f"Erreur transfert : {e}")
        return False

def get_user_transactions(user_id):
    """
    Récupère l'historique GLOBAL (P2P + Opérations Admin)
    Utilisé par la 1ère icône (Global History)
    """
    history = []
    try:
        with get_db_connection() as conn:
            # 1. P2P
            sql_trans = """
                SELECT t.*, s.username as sender_name, r.username as receiver_name 
                FROM transactions t
                LEFT JOIN parieurs s ON t.envoyeur_id = s.id
                LEFT JOIN parieurs r ON t.receveur_id = r.id
                WHERE t.envoyeur_id = ? OR t.receveur_id = ?
            """
            rows_trans = conn.execute(sql_trans, (user_id, user_id)).fetchall()

            for r in rows_trans:
                item = dict(r)
                item["source"] = "p2p"
                if item["envoyeur_id"] == user_id:
                    item["type"] = "envoi"
                    item["display_montant"] = depuis_centimes(item["montant"])
                    item["description"] = f"Envoyé à @{item['receiver_name']}"
                else:
                    item["type"] = "recu"
                    item["display_montant"] = depuis_centimes(item["montant_net"])
                    item["description"] = f"Reçu de @{item['sender_name']}"
                item["sort_date"] = item["processed_at"]
                history.append(item)

            # 2. Admin Actions (Logs manuels)
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

    history.sort(key=lambda x: x["sort_date"], reverse=True)
    return history
