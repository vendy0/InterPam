from database.connection import get_db_connection
from utils.finance import vers_centimes, depuis_centimes
import sqlite3


def get_user_by_email(email):
    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT * FROM parieurs WHERE email = ?", (email,)
        ).fetchone()
        return dict(user) if user else None


def get_user_by_username(username):
    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT * FROM parieurs WHERE username = ?", (username,)
        ).fetchone()
        return dict(user) if user else None


def ajouter_parieur(
    prenom,
    nom,
    username,
    email,
    age,
    classe,
    mdp,
    created_at,
    role="user",
    solde_initial=0,
):
    solde_centimes = vers_centimes(solde_initial)
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO parieurs (prenom, nom, username, email, age, classe, mdp, created_at, role, solde) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    prenom,
                    nom,
                    username,
                    email,
                    age,
                    classe,
                    mdp,
                    created_at,
                    role,
                    solde_centimes,
                ),
            )
            conn.commit()
            return True, "Succès"
    except Exception as e:
        return False, str(e)


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


def get_user_by_email(email):
    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT * FROM parieurs WHERE email = ?", (email,)
        ).fetchone()
        return dict(user) if user else None


def get_user_by_username(username):
    with get_db_connection() as conn:
        user = conn.execute(
            "SELECT * FROM parieurs WHERE username = ?", (username,)
        ).fetchone()
        return dict(user) if user else None


# Ajoute ici tes autres fonctions de filtrage (filtrer_users_admin, etc.)


def get_user_by_name(nom):
    """Récupère un utilisateur par son nom."""
    try:
        with get_db_connection() as conn:
            conn.execute(
                "SELECT * FROM parieurs WHERE prenom LIKE ? OR nom LIKE ?", (nom, nom)
            )
            return conn.fetchall()
    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération (nom) : {e}")
        return None


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


def filtrer_users_admin(criteres):
    """Recherche des utilisateurs correspondant à TOUS les critères fournis."""
    try:
        with get_db_connection() as conn:
            filtres = {k: v for k, v in criteres.items() if v and v.strip() != ""}

            if not filtres:
                return []

            clauses = []
            parametres = []

            for col, val in filtres.items():
                if col in ["nom", "prenom", "username"]:
                    clauses.append(f"{col} LIKE ?")
                    parametres.append(f"%{val}%")
                else:
                    clauses.append(f"{col} = ?")
                    parametres.append(val)

            sql = f"SELECT * FROM parieurs WHERE {' AND '.join(clauses)}"
            conn.execute(sql, parametres)
            return conn.fetchall()
    except sqlite3.Error as e:
        print(f"Erreur recherche dynamique : {e}")
        return []


def get_all_users():
    """Récupérer tous les utilisateurs."""
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT * FROM parieurs ORDER BY prenom ASC")
            return conn.fetchall()
    except Exception as e:
        return f"Erreur lors de la récupération : {e}"
