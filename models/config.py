from database.connexion import get_db_connection
import sqlite3


def get_config():
	"""Récupère la configuration actuelle."""
	try:
		with get_db_connection() as conn:
			config = conn.execute("SELECT * FROM config WHERE id = 1").fetchone()
			return dict(config)
	except Exception as e:
		print(f"Erreur get_config: {e}")
		# Valeurs par défaut en cas d'erreur critique
		return {"caisse_solde": 0, "mise_min": 1000, "mise_max": 100000, "frais_retrait": 0.03}


def update_config_params(mise_min, mise_max, frais_retrait):
	"""Met à jour les paramètres (sauf le solde caisse)."""
	try:
		with get_db_connection() as conn:
			conn.execute(
				"""
                UPDATE config 
                SET mise_min = ?, mise_max = ?, frais_retrait = ? 
                WHERE id = 1
            """,
				(mise_min, mise_max, frais_retrait),
			)
			conn.commit()
			return True
	except Exception as e:
		print(f"Erreur update_config: {e}")
		return False


def update_caisse_manuelle(nouveau_solde_centimes):
	"""Pour l'admin : modifier le montant de départ manuellement."""
	try:
		with get_db_connection() as conn:
			conn.execute(
				"UPDATE config SET caisse_solde = ? WHERE id = 1", (nouveau_solde_centimes,)
			)
			conn.commit()
			return True
	except Exception as e:
		return False


def mouvement_caisse(montant_centimes, operation):
	"""
	Gère les entrées/sorties de la caisse.
	operation: 'add' ou 'sub'
	"""
	try:
		with get_db_connection() as conn:
			if operation == "add":
				conn.execute(
					"UPDATE config SET caisse_solde = caisse_solde + ? WHERE id = 1",
					(montant_centimes,),
				)
			elif operation == "sub":
				# Vérification optionnelle ici, mais faite en amont pour les paris
				conn.execute(
					"UPDATE config SET caisse_solde = caisse_solde - ? WHERE id = 1",
					(montant_centimes,),
				)
			conn.commit()
			return True
	except Exception as e:
		print(f"Erreur mouvement caisse: {e}")
		return False
