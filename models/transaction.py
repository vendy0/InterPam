# models/transaction.py
from database.connexion import get_db_connection
from utils.finance import depuis_centimes, vers_centimes
import sqlite3
from datetime import datetime

# models/transaction.py


def create_transaction(
    user_id, type_trans, montant_dec, telephone, moncash_id=None, frais_dec=0, net_dec=0
):
    try:
        montant_centimes = vers_centimes(montant_dec)
        frais_centimes = vers_centimes(frais_dec)

        # Si c'est un dépôt, le net = le montant brut (pas de frais pour l'instant)
        # Si c'est un retrait, net_dec est passé en argument
        if net_dec == 0 and type_trans == "depot":
            net_centimes = montant_centimes
        else:
            net_centimes = vers_centimes(net_dec)

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with get_db_connection() as conn:
            conn.execute(
                """INSERT INTO transactions 
                (user_id, type, montant, frais, montant_net, telephone, moncash_id, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    type_trans,
                    montant_centimes,
                    frais_centimes,
                    net_centimes,
                    telephone,
                    moncash_id,
                    created_at,
                ),
            )
            conn.commit()
            return True, "Demande enregistrée."
    except sqlite3.IntegrityError:
        return False, "Cet ID de transaction a déjà été utilisé."
    except sqlite3.Error as e:
        return False, f"Erreur base de données : {e}"


# models/transaction.py


def update_transaction_status(
    tx_id, statut, admin_id, raison=None
):  # <-- Ajoute bien admin_id ici
    """Met à jour le statut (valide/refuse) avec l'ID de l'admin."""
    try:
        processed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with get_db_connection() as conn:
            conn.execute(
                """UPDATE transactions 
                   SET statut = ?, processed_at = ?, admin_id = ?, raison_refus = ?
                   WHERE id = ?""",
                (statut, processed_at, admin_id, raison, tx_id),
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Erreur update_transaction_status: {e}")
        return False


def _process_transaction_row(row):
    """Helper pour formater les lignes de transaction"""
    t = dict(row)
    t["montant"] = depuis_centimes(t["montant"])  # Brut
    # On gère le cas où les colonnes seraient nulles (anciennes transactions)
    t["frais"] = depuis_centimes(t["frais"]) if t["frais"] else 0
    t["montant_net"] = (
        depuis_centimes(t["montant_net"]) if t["montant_net"] else t["montant"]
    )
    return t


def get_user_transactions(user_id):
    try:
        with get_db_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
            return [_process_transaction_row(r) for r in cur.fetchall()]
    except sqlite3.Error as e:
        print(f"Erreur: {e}")
        return []


def get_pending_transactions():
    """Récupère toutes les transactions en attente pour l'admin avec infos user."""
    try:
        with get_db_connection() as conn:
            query = """
                SELECT t.*, p.username, p.prenom, p.nom 
                FROM transactions t
                JOIN parieurs p ON t.user_id = p.id
                WHERE t.statut = 'en_attente'
                ORDER BY t.created_at ASC
            """
            cur = conn.execute(query)
            return [_process_transaction_row(r) for r in cur.fetchall()]
    except sqlite3.Error as e:
        print(f"Erreur get_pending_transactions: {e}")
        return []


def get_transaction_by_id(tx_id):
    try:
        with get_db_connection() as conn:
            cur = conn.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,))
            res = cur.fetchone()
            if res:
                t = dict(res)
                t["montant_dec"] = depuis_centimes(t["montant"])  # Helper
                return t
            return None
    except Exception as e:
        return None


def get_transaction_history():
    """Récupère toutes les transactions traitées (validées/refusées)."""
    try:
        with get_db_connection() as conn:
            query = """
                SELECT t.*, p.username, admin.prenom as admin_prenom, admin.nom as admin_nom
                FROM transactions t
                JOIN parieurs p ON t.user_id = p.id
                LEFT JOIN parieurs admin ON t.admin_id = admin.id
                WHERE t.statut != 'en_attente'
                ORDER BY t.processed_at DESC
            """
            cur = conn.execute(query)
            return [_process_transaction_row(r) for r in cur.fetchall()]
    except sqlite3.Error as e:
        print(f"Erreur get_transaction_history: {e}")
        return []
