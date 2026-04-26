import sqlite3
import csv
import os
from datetime import datetime
from read_datas import main_to_excel
from pathlib import Path

# Configuration
DB_NAME = "interpam.db"
DATE_EXPORT = datetime.now().strftime("%d-%m-%Y_%H-%M")
EXPORT_DIR = f"exports_complets_{DATE_EXPORT}"
EXPORT_DIR_CSV = Path(f"./{EXPORT_DIR}").joinpath("CSV")

# Colonnes d'argent (Conversion centimes -> HTG)
MONEY_COLUMNS = [
    "solde",
    "mise",
    "gain_potentiel",
    "montant",
    "frais",
    "montant_net",
    "caisse_solde",
    "mise_min",
    "mise_max",
    "cote",
]

# Colonnes à masquer
EXCLUDE_COLUMNS = ["mdp", "token"]

# --- FONCTIONS UTILITAIRES ---


def convert_money(col_name, value):
    """Convertit centimes en HTG, sauf si c'est null"""
    if value is None:
        return ""
    try:
        # Si c'est une cote, on garde tel quel (souvent float), sinon on divise par 100
        if col_name == "cote":
            return float(value)
        return float(value) / 100
    except:
        return value


def get_display_name(table_name, row):
    """
    Cette fonction 'MAGIQUE' décide comment afficher une ligne d'une autre table.
    Elle remplace l'ID par du texte lisible.
    """
    if not row:
        return "Inconnu"

    # 1. Pour les PARIEURS (et Admins)
    if table_name == "parieurs":
        return (
            f"{row.get('prenom', '')} {row.get('nom', '')} (@{row.get('username', '')})"
        )

    # 2. Pour les MATCHS
    if table_name == "matchs":
        return (
            f"{row.get('equipe_a')} vs {row.get('equipe_b')} ({row.get('date_match')})"
        )

    # 3. Pour les OPTIONS
    if table_name == "options":
        return f"{row.get('libelle')} (Cote: {row.get('cote')})"

    # 4. Générique (cherche un champ 'nom', 'titre', 'label')
    for key in ["libelle", "nom", "name", "title", "description", "email"]:
        if key in row:
            return str(row[key])

    # 5. Fallback : retourne l'ID si on ne trouve rien de mieux
    return str(row.get("id", "?"))


def load_foreign_key_map(cursor, table_name):
    """
    Récupère la liste des colonnes qui sont des clés étrangères
    Retourne : { 'parieur_id': 'parieurs', 'match_id': 'matchs' }
    """
    fk_map = {}
    try:
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        # row: (id, seq, table, from, to, on_update, on_delete, match)
        for row in cursor.fetchall():
            col_from = row[3]  # La colonne dans la table actuelle (ex: parieur_id)
            table_to = row[2]  # La table visée (ex: parieurs)
            fk_map[col_from] = table_to
    except:
        pass
    return fk_map


def cache_reference_tables(cursor, fk_map):
    """
    Charge les données des tables liées en mémoire pour aller vite.
    Retourne : { 'parieurs': { 1: {'nom': 'Jean'...}, 2: {...} } }
    """
    cache = {}
    unique_target_tables = set(fk_map.values())

    for target_table in unique_target_tables:
        try:
            # On récupère tout pour avoir les noms
            cursor.execute(f"SELECT * FROM {target_table}")
            rows = cursor.fetchall()

            # On convertit en dictionnaire par ID
            # On a besoin des noms de colonnes pour get_display_name
            col_names = [d[0] for d in cursor.description]

            table_cache = {}
            for r in rows:
                # Créer un dict {col: val} pour cette ligne
                row_dict = {col_names[i]: r[i] for i in range(len(col_names))}
                # L'ID est supposé être la première colonne ou s'appeler 'id'
                row_id = row_dict.get("id")
                if row_id:
                    table_cache[row_id] = row_dict

            cache[target_table] = table_cache
        except Exception as e:
            print(f"⚠️ Impossible de charger la référence pour {target_table}: {e}")

    return cache


def export_table_smart(cursor, table_name, folder):
    print(f"📦 Traitement de '{table_name}'...", end=" ")

    # 1. Récupérer les données brutes
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        col_names = [d[0] for d in cursor.description]
    except Exception as e:
        print(f"Erreur: {e}")
        return

    # 2. Analyser les Clés Étrangères (Foreign Keys)
    fk_map = load_foreign_key_map(cursor, table_name)

    # 3. Pré-charger les données liées (pour ne pas faire 1000 requêtes SQL)
    ref_cache = cache_reference_tables(cursor, fk_map)

    # 4. Écriture CSV
    filename = os.path.join(folder, f"{table_name}.csv")
    with open(filename, "w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")

        # En-têtes (filtrés)
        headers = [c for c in col_names if c not in EXCLUDE_COLUMNS]
        writer.writerow(headers)

        indices_to_keep = [
            i for i, col in enumerate(col_names) if col not in EXCLUDE_COLUMNS
        ]

        count = 0
        for row in rows:
            clean_row = []
            for i in indices_to_keep:
                col_name = col_names[i]
                val = row[i]

                # A. Est-ce une clé étrangère ? (ex: parieur_id)
                if col_name in fk_map:
                    target_table = fk_map[col_name]
                    # Récupérer l'objet complet dans le cache
                    target_row = ref_cache.get(target_table, {}).get(val)
                    # Générer le nom lisible
                    val = get_display_name(target_table, target_row)

                # B. Est-ce de l'argent ?
                elif col_name in MONEY_COLUMNS and isinstance(val, int):
                    val = convert_money(col_name, val)

                # C. Est-ce un booléen/statut spécial ?
                elif col_name == "winner":
                    map_win = {0: "En cours", 1: "Gagné", 2: "Perdu", 3: "Annulé"}
                    val = map_win.get(val, val)
                elif col_name == "actif":
                    val = "Oui" if val == 1 else "Non"

                clean_row.append(val)

            writer.writerow(clean_row)
            count += 1
    print(f"✅ ({count} lignes)")


def main():
    if not os.path.exists(DB_NAME):
        print("❌ Base de données introuvable.")
        return

    os.makedirs(EXPORT_DIR_CSV, exist_ok=True)
    print(f"📂 Dossier d'export : {EXPORT_DIR_CSV}\n")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # Récupérer la liste des tables
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence';"
    )
    tables = [r[0] for r in cur.fetchall()]

    for table in tables:
        export_table_smart(cur, table, EXPORT_DIR_CSV)

    conn.close()
    print(f"\n✨ Terminé ! Les IDs ont été remplacés par des noms.")


if __name__ == "__main__":
    print("DÉBUT DU TRAITEMENT".center(50, "_"), "\n\n")
    main()
    main_to_excel(Path(EXPORT_DIR), Path(EXPORT_DIR_CSV), DATE_EXPORT)
    print("\n", "FIN DU TRAITEMENT".center(50, "_"), "\n")
