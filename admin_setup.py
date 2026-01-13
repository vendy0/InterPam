# setup_admin.py
import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime
from database.setup import initialiser_bdd

DB_NAME = "database.db"  # chemin exact


def main():
    print("--- INSTALLATION DU SUPER ADMIN INTERPAM ---")

    initialiser_bdd()

    prenom = "Andy V."
    nom = "Descartes"
    username = "Vendy"
    email = "andyvenson99@gmail.com"
    mdp = "genetique"

    try:
        with sqlite3.connect("interpam.db") as conn:
            cur = conn.cursor()

            # Vérifier s'il existe déjà
            cur.execute("SELECT id FROM parieurs WHERE role = 'super_admin' LIMIT 1")
            if cur.fetchone():
                print("❌ Un super admin existe déjà. Abandon.")
                return

            hash_mdp = generate_password_hash(mdp)
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cur.execute(
                """
                INSERT INTO parieurs
                (prenom, nom, username, email, age, classe, mdp, created_at, role, solde)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prenom,
                    nom,
                    username,
                    email,
                    99,
                    "Direction",
                    hash_mdp,
                    created_at,
                    "super_admin",
                    200000,
                ),
            )

            conn.commit()

        print("✅ Super admin créé avec succès")
        print(f"➡️ Identifiants : {username} / {mdp}")

    except sqlite3.Error as e:
        print(f"❌ Erreur BDD : {e}")


if __name__ == "__main__":
    main()
