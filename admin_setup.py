# setup_admin.py
from data import creer_super_admin, initialiser_bdd

def main():
    print("--- INSTALLATION DU SUPER ADMIN INTERPAM ---")
    
    # On s'assure que la BDD existe
    initialiser_bdd()
    
    # Remplace par tes vraies infos
    prenom = "Andy V."
    nom = "Descarted"
    username = "Anonymous"
    email = "klyrolly0@gmail.com"
    mdp = "Vendy_317" # Change-le !

    succes, message = creer_super_admin(prenom, nom, username, email, mdp)
    
    if succes:
        print(f"✅ {message}")
        print(f"Identifiants : {username} / {mdp}")
    else:
        print(f"❌ {message}")

if __name__ == "__main__":
    main()
