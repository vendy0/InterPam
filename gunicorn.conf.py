# gunicorn.conf.py
import multiprocessing

# 1. Adresse et Port
# '0.0.0.0' permet d'écouter sur toutes les interfaces (utile pour Docker/Twilight Paradox)
bind = "0.0.0.0:2037"

# 2. Performance & Workers
# Formule standard : (2 x nombre de coeurs CPU) + 1
# Pour InterPam, cela permet de gérer les calculs de cotes en parallèle sans bloquer l'UI
workers = multiprocessing.cpu_count() * 2 + 1

# Type de worker : 'sync' est très stable.
# Si vous avez beaucoup de requêtes longues (API), 'gevent' est une alternative.
worker_class = "sync"

# 3. Sécurité & Timeouts
# 30 secondes suffisent largement pour traiter un pari ou valider une invitation
timeout = 30
keepalive = 2

# 4. Journalisation (Logging)
# Indispensable pour débugger les erreurs de data.py en production
accesslog = "-"  # '-' signifie sortie standard (stdout)
errorlog = "-"
loglevel = "info"

# 5. Process Naming
# Pratique pour identifier le processus dans 'top' ou 'htop' sur le serveur
proc_name = "interpam_gunicorn"

# 6. Gestion du code
# Relance automatiquement le serveur si le code change (utile uniquement en dev/staging)
# reload = True
