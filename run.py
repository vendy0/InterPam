from routes import app
from database.setup import initialiser_bdd

initialiser_bdd()
if __name__ == "__main__":
    app.run(debug=True)
