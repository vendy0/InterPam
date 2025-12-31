from database.connexion import get_db_connection
from utils.finance import vers_centimes, depuis_centimes
import sqlite3


def ajouter_parieur(user_data):
    """Ajoute un parieur avec gestion d'exception et tabulation."""
    try:
        role = user_data.get("role", "parieur")
        with get_db_connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "INSERT INTO parieurs (prenom, nom, username, email, age, classe, mdp, role, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    user_data["prenom"],
                    user_data["nom"],
                    user_data["username"],
                    user_data["email"],
                    user_data["age"],
                    user_data["classe"],
                    user_data["mdp"],
                    role,
                    user_data["created_at"],
                ),
            )
            print(f"Utilisateur {user_data['username']} ajouté.")
    except sqlite3.Error as e:
        print(f"Erreur SQL lors de l'ajout du parieur : {e}")


def get_user_by_name(nom):
    """Récupère un utilisateur par son nom."""
    try:
        with get_db_connection() as conn:
            conn.execute(
                "SELECT * FROM parieurs WHERE prenom LIKE ? OR nom LIKE ?", (nom, nom)
            )
            rows = cur.fetchall()

            users_list = []
            for row in rows:
                # On transforme l'objet Row en dictionnaire pour pouvoir le modifier
                user_dict = dict(row)
                # Conversion du solde pour chaque utilisateur
                user_dict["solde"] = depuis_centimes(user_dict["solde"])
                users_list.append(user_dict)

            return users_list
    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération (nom) : {e}")
        return None


def get_user_by_email(email):
    try:
        with get_db_connection() as conn:
            user = conn.execute(
                "SELECT * FROM parieurs WHERE email = ?", (email,)
            ).fetchone()
            return dict(user) if user else None
    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération (email) : {e}")
        return None


def get_user_by_username(username):
    """Récupère un utilisateur par son username."""
    try:
        with get_db_connection() as conn:
            cur = conn.execute("SELECT * FROM parieurs WHERE username = ?", (username,))
            user = cur.fetchone()
            if user:
                user_dict = dict(user)
                user_dict["solde"] = depuis_centimes(user_dict["solde"])
                return user_dict
            return None
    except sqlite3.Error as e:
        print(f"Erreur : {e}")
        return None


def get_users(key=None, result=None):
    """Récupère une liste d'utilisateurs avec conversion du solde."""
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()

            if key and result:
                # ATTENTION : On injecte 'key' car c'est un nom de colonne,
                # mais on utilise '?' pour la valeur 'result' par sécurité.
                query = f"SELECT * FROM parieurs WHERE {key} = ? AND actif = 1"
                cur.execute(query, (result,))
            else:
                cur.execute("SELECT * FROM parieurs WHERE actif = 1")

            rows = cur.fetchall()

            users_list = []
            for row in rows:
                # On transforme l'objet Row en dictionnaire pour pouvoir le modifier
                user_dict = dict(row)
                # Conversion du solde pour chaque utilisateur
                user_dict["solde"] = depuis_centimes(user_dict["solde"])
                users_list.append(user_dict)

            return users_list  # Retourne une liste de dictionnaires
    except sqlite3.Error as e:
        print(f"Erreur : {e}")
        return []


def filtrer_users_admin(filtres):
    try:
        with get_db_connection() as conn:
            clauses = []
            parametres = []
            for col, val in filtres.items():
                if val:
                    clauses.append(f"{col} LIKE ?")
                    parametres.append(f"%{val}%")

            sql = "SELECT * FROM parieurs"
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)

            users = conn.execute(sql, parametres).fetchall()
            return [dict(u) for u in users]
    except Exception:
        return []


def get_user_by_age(age):
    """Récupère un utilisateur par son age."""
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT * FROM parieurs WHERE age = ?", (age,))
            return conn.fetchall()
    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération (age) : {e}")
        return None


def get_user_by_grade(classe):
    """Récupère un utilisateur par sa classe."""
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT * FROM parieurs WHERE classe = ?", (classe,))
            return conn.fetchall()
    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération (username) : {e}")
        return None


def credit(username, montant_decimal):
    try:
        solde_centimes = vers_centimes(montant_decimal)
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE parieurs SET solde = solde + ? WHERE username = ?",
                (solde_centimes, username),
            )
            conn.commit()
            return True, "Compte crédité"
    except Exception as e:
        return False, str(e)


def debit(username, montant_decimal):
    try:
        solde_centimes = vers_centimes(montant_decimal)
        with get_db_connection() as conn:
            user = get_user_by_username(username)
            if solde_centimes < user["solde"]:
                conn.execute(
                    "UPDATE parieurs SET solde = solde - ? WHERE username = ?",
                    (solde_centimes, username),
                )
                conn.commit()
                return True, "Compte débité"
            else:
                return False, "Solde insuffisant !"
    except sqlite3.Error as e:
        return False, f"Erreur lors du débit {e}"
