from routes import app
from database.setup import initialiser_bdd

initialiser_bdd()

if __name__ == "__main__":
    # host='0.0.0.0' dit à Flask d'écouter toutes les adresses, pas juste localhost
    app.run(host='0.0.0.0', port=5000, debug=False)
