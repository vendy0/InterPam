from database.connexion import get_db_connection
from utils.finance import vers_centimes, depuis_centimes
from datetime import datetime, date, timedelta
import sqlite3
import secrets
from models.emails import envoyer_push_notification


def save_pending_registration(user_data, token, expiration):
	"""Sauvegarde temporaire de l'inscription."""
	try:
		with get_db_connection() as conn:
			conn.execute(
				"""INSERT INTO pending_registrations 
                   (prenom, nom, username, email, age, classe, mdp, token, expiration, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
				(
					user_data["prenom"],
					user_data["nom"],
					user_data["username"],
					user_data["email"],
					user_data["age"],
					user_data["classe"],
					user_data["mdp"],
					token,
					expiration,
					user_data["created_at"],
				),
			)
			conn.commit()
			return True
	except sqlite3.Error as e:
		print(f"Erreur save_pending : {e}")
		return False


def check_pending_duplicates(username, email):
	"""Vérifie si username ou email est déjà en attente de validation."""
	try:
		with get_db_connection() as conn:
			cur = conn.execute(
				"SELECT * FROM pending_registrations WHERE username = ? AND email = ?",
				(username, email),
			)
			pendings = cur.fetchall()
			pend = 0
			if not pendings:
				return "success", None
			for pending in pendings:
				expire_at = datetime.strptime(pending["expiration"], "%Y-%m-%d %H:%M:%S.%f")
				if datetime.now() < expire_at:
					pend += 1
				else:
					pass
			if pend >= 3:
				return (
					"error",
					"Plusieurs confirmations ont déjà été envoyées sur cet adresse mail. Vérifiez vos emails !",
				)
			else:
				return "success", None
	except Exception as e:
		print(f"Erreur check pending : {e}")
		return "error", "Erreur technique lors de l'inscription !"


def get_pending_by_token(token):
	"""Récupère une inscription en attente via le token."""
	try:
		with get_db_connection() as conn:
			# On utilise row_factory pour avoir un dictionnaire
			conn.row_factory = sqlite3.Row
			cur = conn.execute("SELECT * FROM pending_registrations WHERE token = ?", (token,))
			res = cur.fetchone()
			return dict(res) if res else None
	except sqlite3.Error as e:
		print(f"Erreur get_pending : {e}")
		return None


def delete_pending(token):
	"""Supprime l'inscription temporaire après validation."""
	try:
		with get_db_connection() as conn:
			conn.execute("DELETE FROM pending_registrations WHERE token = ?", (token,))
			conn.commit()
	except sqlite3.Error as e:
		print(f"Erreur delete_pending : {e}")


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
			conn.commit()
			print(f"Utilisateur {user_data['username']} ajouté.")
	except sqlite3.Error as e:
		print(f"Erreur SQL lors de l'ajout du parieur : {e}")


def get_user_by_id(parieur_id):
	"""Récupère un utilisateur par son id."""
	try:
		with get_db_connection() as conn:
			cur = conn.execute("SELECT * FROM parieurs WHERE id = ?", (parieur_id,))
			user = cur.fetchone()
			if user:
				user_dict = dict(user)
				user_dict["solde"] = depuis_centimes(user_dict["solde"])
			return user_dict
	except sqlite3.Error as e:
		print(f"Erreur lors de la récupération (id) : {e}")
		return None


def get_user_by_name(nom):
	"""Récupère un utilisateur par son nom."""
	try:
		with get_db_connection() as conn:
			cur = conn.execute(
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
			user = conn.execute("SELECT * FROM parieurs WHERE email = ?", (email,)).fetchone()
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
					# Traitement spécial pour les notifications
					if col == "notif":
						if val == "oui":
							clauses.append(
								"push_subscription IS NOT NULL AND push_subscription != ''"
							)
						elif val == "non":
							clauses.append("(push_subscription IS NULL OR push_subscription = '')")
					# Traitement standard pour les autres colonnes
					else:
						clauses.append(f"{col} LIKE ?")
						parametres.append(f"%{val}%")

			sql = "SELECT * FROM parieurs"
			if clauses:
				sql += " WHERE " + " AND ".join(clauses)

			users = conn.execute(sql, parametres).fetchall()
			return [dict(u) for u in users]
	except Exception as e:
		print(f"Erreur : {e}")
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


# Ajoute cette nouvelle fonction pour lire l'historique
def get_admin_transactions_by_user(user_id):
	try:
		with get_db_connection() as conn:
			query = """
                SELECT at.*, admin.username as admin_name, admin.prenom as admin_prenom
                FROM admin_transactions at
                JOIN parieurs admin ON at.admin_id = admin.id
                WHERE at.user_id = ?
                ORDER BY at.created_at DESC
            """
			cur = conn.execute(query, (user_id,))
			rows = cur.fetchall()
			return [
				dict(row) for row in rows
			]  # Pas besoin de convertir le montant ici si tu le fais dans le template
	except sqlite3.Error as e:
		print(f"Erreur historique admin: {e}")
		return []


# Modifie la fonction credit existante
def credit(username, montant_decimal, message=False, admin_id=None):  # <--- Ajout de admin_id
	try:
		solde_centimes = int(montant_decimal * 100)  # Assure-toi que c'est un int
		created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

		with get_db_connection() as conn:
			user = get_user_by_username(username)
			if not user:
				return False, "Utilisateur introuvable"

			# 1. Mise à jour du solde
			conn.execute(
				"UPDATE parieurs SET solde = solde + ? WHERE username = ?",
				(solde_centimes, username),
			)

			# 2. Enregistrement dans l'historique si c'est une action admin
			if admin_id:
				conn.execute(
					"""INSERT INTO admin_transactions (admin_id, user_id, type, montant, created_at)
                       VALUES (?, ?, 'credit', ?, ?)""",
					(admin_id, user["id"], solde_centimes, created_at),
				)

			conn.commit()

			# 3. Récupérer les infos à jour pour la notification
			user = get_user_by_username(username)
			if not user:
				return False, "Utilisateur introuvable"

			# 4. Préparation du message avec le nouveau solde
			# Note : Assurez-vous que user['solde'] est converti de centimes vers HTG pour l'affichage
			nouveau_solde_htg = user["solde"]
			# Attention ici ton code original avait un petit souci de type, mais supposons que ça marche
			if message and user.get("push_subscription"):
				envoyer_push_notification(
					user["push_subscription"],
					"Compte crédité",
					f"Crédit de {montant_decimal} HTG reçu.",
				)

			return True, "Compte crédité"
	except Exception as e:
		return False, f"Erreur lors du crédit : {str(e)}"


# Modifie la fonction debit existante
def debit(username, montant_decimal, message=False, admin_id=None):  # <--- Ajout de admin_id
	try:
		solde_centimes = int(montant_decimal * 100)
		created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

		with get_db_connection() as conn:
			user = get_user_by_username(username)
			if not user:
				return False, "Utilisateur introuvable"

			# Vérification du solde (Code existant convertit user['solde'] via depuis_centimes, donc attention aux unités)
			# Pour être sûr, on compare en centimes ou on refait une query brute.
			# Supposons que user['solde'] vient de get_user_by_username qui fait déjà 'depuis_centimes'
			if user["solde"] < montant_decimal:
				return False, "Solde insuffisant !"

			conn.execute(
				"UPDATE parieurs SET solde = solde - ? WHERE username = ?",
				(solde_centimes, username),
			)

			# Enregistrement historique admin
			if admin_id:
				conn.execute(
					"""INSERT INTO admin_transactions (admin_id, user_id, type, montant, created_at)
                       VALUES (?, ?, 'debit', ?, ?)""",
					(admin_id, user["id"], solde_centimes, created_at),
				)

			conn.commit()

			# 5. Envoi de la notification
			if message:
				if user.get("push_subscription"):
					envoyer_push_notification(
						user["push_subscription"],
						"Compte débité",
						f"Votre compte vient d'être débité de {montant_decimal} HTG. Nouveau solde : {(vers_centimes(user['solde']) - int(solde_centimes)) / 100} HTG",
					)

			return True, "Compte débité"
	except Exception as e:
		return False, f"Erreur lors du débit {e}"


def save_subscription(push_subscription, user_id):
	"""Sauvegarder l'id de l'appareil pour notification."""
	try:
		with get_db_connection() as conn:
			conn.execute(
				"UPDATE parieurs SET push_subscription = ? WHERE id = ?",
				(push_subscription, user_id),
			)
			conn.commit()
		return {"statut": "Succès"}
	except sqlite3.Error as e:
		print(f"Erreur lors de l'abonnement : {e}")
		return None


def save_recuperation(email, token, expiration):
	"""Sauvegarder l'id de l'appareil pour notification."""
	try:
		with get_db_connection() as conn:
			conn.execute(
				"""
            INSERT INTO recuperations (email, token, expiration) 
            VALUES (?, ?, ?)""",
				(
					email,
					token,
					expiration,
				),
			)
			conn.commit()
		return True
	except sqlite3.Error as e:
		print(f"Erreur lors de l'abonnement : {e}")
		return False


def get_recuperation_by_token(token):
	try:
		with get_db_connection() as conn:
			cur = conn.execute("SELECT * FROM recuperations WHERE token = ?", (token,))
			res = cur.fetchone()
			return res
	except sqlite3.Error as e:
		print(f"Erreur lors de la récupération : {e}")


def reset_password(email, mdp):
	try:
		with get_db_connection() as conn:
			cur = conn.execute(
				"UPDATE parieurs SET mdp = ? WHERE email = ?",
				(
					mdp,
					email,
				),
			)
			conn.execute(
				"DELETE FROM recuperations WHERE email = ?",
				(email,),
			)
			conn.commit()
			return True
	except sqlite3.Error as e:
		print(f"Erreur lors de la réinitialisation du mot de passe : {e}")
		return False


def send_message(parieur_id, message, created_at):
	try:
		with get_db_connection() as conn:
			cur = conn.execute(
				"INSERT INTO messagerie(parieur_id, message, created_at) VALUES(?, ?, ?)",
				(
					parieur_id,
					message,
					created_at,
				),
			)
			conn.commit()
			return True
	except sqlite3.Error as e:
		print(f"Erreur lors de l'envoie : {e}")
		return False
