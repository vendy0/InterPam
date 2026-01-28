import sqlite3
import csv
import os
from datetime import datetime

# Configuration
DB_NAME = "interpam.db"
EXPORT_DIR = f"exports_{datetime.now().strftime('%Y-%m-%d_%H-%M')}"

# Liste des colonnes qui contiennent de l'argent (en centimes) et doivent être converties
MONEY_COLUMNS = [
    "solde", "mise", "gain_potentiel", "montant", 
    "frais", "montant_net", "caisse_solde", 
    "mise_min", "mise_max"
]

# Colonnes à exclure pour la sécurité
EXCLUDE_COLUMNS = ["mdp", "token"] 

def convert_centimes(value):
    """Convertit les centimes en HTG (float)"""
    try:
        if value is None: return 0.0
        return float(value) / 100
    except (ValueError, TypeError):
        return value

def get_tables(cursor):
    """Récupère la liste de toutes les tables"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    # On exclut la table interne de sqlite
    return [t for t in tables if t != "sqlite_sequence"]

def export_table(cursor, table_name, folder):
    """Exporte une table spécifique en CSV"""
    print(f"📦 Export de la table '{table_name}'...", end=" ")
    
    # 1. Récupérer les données
    try:
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Erreur : {e}")
        return

    # 2. Récupérer les noms de colonnes
    col_names = [description[0] for description in cursor.description]
    
    # 3. Préparer le fichier CSV
    filename = os.path.join(folder, f"{table_name}.csv")
    
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=';') # Point-virgule pour Excel/Calc facile
        
        # Filtrer les colonnes (exclure mdp)
        headers = [c for c in col_names if c not in EXCLUDE_COLUMNS]
        writer.writerow(headers)
        
        indices_to_keep = [i for i, col in enumerate(col_names) if col not in EXCLUDE_COLUMNS]
        
        count = 0
        for row in rows:
            clean_row = []
            for i in indices_to_keep:
                col_name = col_names[i]
                val = row[i]
                
                # Conversion Argent (Centimes -> HTG)
                if col_name in MONEY_COLUMNS and isinstance(val, int):
                    val = convert_centimes(val)
                
                # Conversion Booléen (pour lisibilité)
                if col_name in ['actif', 'winner', 'read'] and val in [0, 1]:
                    # Cas spécifique winner (0=En cours, 1=Gagné, 2=Perdu, 3=Annulé)
                    if col_name == 'winner':
                         map_win = {0: 'En cours', 1: 'Gagné', 2: 'Perdu', 3: 'Annulé'}
                         val = map_win.get(val, val)
                    elif col_name == 'actif':
                        val = 'Oui' if val == 1 else 'Non'
                    
                clean_row.append(val)
            
            writer.writerow(clean_row)
            count += 1
            
    print(f"✅ ({count} lignes)")

def main():
    if not os.path.exists(DB_NAME):
        print(f"❌ Erreur : La base de données {DB_NAME} est introuvable.")
        return

    # Création du dossier d'export
    os.makedirs(EXPORT_DIR, exist_ok=True)
    print(f"📂 Dossier créé : {EXPORT_DIR}\n")

    try:
        conn = sqlite3.connect(DB_NAME)
        # Permet d'accéder aux colonnes par index
        conn.row_factory = None 
        cur = conn.cursor()

        tables = get_tables(cur)
        
        for table in tables:
            export_table(cur, table, EXPORT_DIR)
            
        print(f"\n✨ Terminé ! Tes fichiers CSV sont dans le dossier '{EXPORT_DIR}'.")
        
    except sqlite3.Error as e:
        print(f"❌ Erreur SQL globale : {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
