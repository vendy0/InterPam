from database.connexion import get_db_connection
from utils.finance import vers_centimes, depuis_centimes
import sqlite3


def get_config():
    """Récupère la configuration actuelle."""
    try:
        with get_db_connection() as conn:
            config = conn.execute("SELECT * FROM config WHERE id = 1").fetchone()

            # Correction ici : on retire l'appel à {e} qui n'existe pas
            if not config:
                print("Erreur get_config: Configuration introuvable en BDD (ID 1)")
                return {
                    "caisse_solde": 0,
                    "mise_min": 1000,  # mis en centimes pour correspondre à votre logique
                    "mise_max": 100000,
                    "frais_retrait": 0.03,
                }

            config = dict(config)
            config["caisse_solde"] = depuis_centimes(config["caisse_solde"])
            config["mise_min"] = depuis_centimes(config["mise_min"])
            config["mise_max"] = depuis_centimes(config["mise_max"])
            return config  # IMPORTANT : Ne pas oublier de retourner config à la fin du try !

    except Exception as e:
        print(f"Erreur critique get_config: {e}")
        return {
            "caisse_solde": 0,
            "mise_min": 10,
            "mise_max": 1000,
            "frais_retrait": 0.03,
        }


def update_config_params(mise_min_dec, mise_max_dec, frais_retrait):
    """Met à jour les paramètres (sauf le solde caisse)."""
    mise_min_cent = vers_centimes(mise_min_dec)
    mise_max_cent = vers_centimes(mise_max_dec)
    try:
        with get_db_connection() as conn:
            conn.execute(
                """
                UPDATE config 
                SET mise_min = ?, mise_max = ?, frais_retrait = ? 
                WHERE id = 1
            """,
                (mise_min_cent, mise_max_cent, frais_retrait),
            )
            conn.commit()
            return True
    except Exception as e:
        print(f"Erreur update_config: {e}")
        return False


def update_caisse_manuelle(nouveau_solde_dec):
    """Pour l'admin : modifier le montant de départ manuellement."""
    nouveau_solde_centimes = vers_centimes(nouveau_solde_dec)
    try:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE config SET caisse_solde = ? WHERE id = 1",
                (nouveau_solde_centimes,),
            )
            conn.commit()
            return True
    except Exception as e:
        return False


def mouvement_caisse(montant_dec, operation, conn=None):
    """
    Gère les entrées/sorties de la caisse.
    operation: 'add' ou 'sub'
    """
    montant_centimes = vers_centimes(montant_dec)
    try:
        if not conn:
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
        else:
            # On utilise la connexion existante passée par la fonction parente
            if operation == "add":
                conn.execute(
                    "UPDATE config SET caisse_solde = caisse_solde + ? WHERE id = 1",
                    (montant_centimes,),
                )
            elif operation == "sub":
                conn.execute(
                    "UPDATE config SET caisse_solde = caisse_solde - ? WHERE id = 1",
                    (montant_centimes,),
                )
        return True
    except Exception as e:
        print(f"Erreur mouvement caisse: {e}")
        return False
