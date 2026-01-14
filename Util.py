from database.connexion import get_db_connection


try:
	# 1. On commence une transaction pour la sécurité
	with get_db_connection() as conn:
		cur = conn.execute("BEGIN TRANSACTION")
		# 2. On renomme la table actuelle
		cur = conn.execute("ALTER TABLE pending_registrations RENAME TO pending_registrations_old")

		# 3. On crée la nouvelle table avec la contrainte UNIQUE sur 'email'
		cur.execute("""CREATE TABLE IF NOT EXISTS pending_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                prenom TEXT NOT NULL,
                nom TEXT NOT NULL,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                age INT NOT NULL,
                classe TEXT NOT NULL,
                mdp TEXT NOT NULL,
                token TEXT NOT NULL,
                expiration TEXT NOT NULL,
                created_at TEXT NOT NULL
            )""")

		# 4. On transfère les données
		# Note : S'il y a déjà des doublons, cette étape échouera.
		cur = conn.execute(
			"INSERT INTO pending_registrations (id, prenom, nom, username, email, age, classe, mdp, token, expiration, created_at) SELECT id, prenom, nom, username, email, age, classe, mdp, token, expiration, created_at FROM pending_registrations_old"
		)

		# 5. On supprime l'ancienne table et on valide
		cur = conn.execute("DROP TABLE pending_registrations_old")
		conn.commit()
		print("Contrainte supprimé avec succès !")
except Exception as e:
	print(f"Erreur : {e}")
