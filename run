import subprocess
import sys
import os # Ajouté pour gérer les ports
from database.setup import initialiser_bdd

# 1. Initialisation de la base de données (essentiel pour le CIF)
initialiser_bdd()

if __name__ == "__main__":
    # 2. Configuration de la commande Gunicorn via le module python
    # On remplace "gunicorn" par "python", "-m", "gunicorn"
    cmd = [
        sys.executable, "-m", "gunicorn",
        "-c", "gunicorn.conf.py",
        "routes:app"
    ]

    print(f"🚀 Démarrage d'InterPam avec Gunicorn sur le port {os.environ.get('SERVER_PORT', '8000')}...")
    
    try:
        # 3. Lancement du processus
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"❌ Une erreur est survenue lors du lancement de Gunicorn : {e}")
        # On affiche le chemin pour aider au débug
        print(f"DEBUG: Python Executable: {sys.executable}")
        sys.exit(1)
