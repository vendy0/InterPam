# models/transaction.py
from database.connexion import get_db_connection
from utils.finance import depuis_centimes, vers_centimes
import sqlite3
from datetime import datetime

# models/transaction.py


def create_transaction(user_id, type_trans, montant_dec, telephone, moncash_id=None):
    try:
        montant_centimes = vers_centimes(montant_dec)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with get_db_connection() as conn:
            conn.execute(
                """INSERT INTO transactions 
                (user_id, type, montant, telephone, moncash_id, created_at) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    type_trans,
                    montant_centimes,
                    telephone,
                    moncash_id,
                    created_at,
                ),
            )
            conn.commit()
            return True, "Demande enregistrée."
    except sqlite3.IntegrityError:
        # C'est ici qu'on bloque l'utilisation d'un ancien message
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


def get_user_transactions(user_id):
    """Récupère l'historique d'un utilisateur."""
    try:
        with get_db_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
            rows = cur.fetchall()
            txs = []
            for r in rows:
                t = dict(r)
                t["montant"] = depuis_centimes(t["montant"])
                txs.append(t)
            return txs
    except sqlite3.Error as e:
        print(f"Erreur get_user_transactions: {e}")
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
            rows = cur.fetchall()
            txs = []
            for r in rows:
                t = dict(r)
                t["montant"] = depuis_centimes(t["montant"])
                txs.append(t)
            return txs
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
