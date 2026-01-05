import os
# from dotenv import load_dotenv
# 
# load_dotenv()
key = "AIzaSyAIRbQY1gaRogSstLwc6xKbL3IDtj0tLzA"

print(f"--- Diagnostic Clé API ---")
if key is None:
    print("RÉSULTAT : Clé non trouvée (None). Vérifiez le nom du fichier .env")
elif key.strip() != key:
    print(f"RÉSULTAT : La clé contient des espaces ou des sauts de ligne invisibles !")
else:
    print(f"RÉSULTAT : Clé chargée. Longueur: {len(key)} caractères.")
    print(f"Début : {key[:4]}... Fin : ...{key[-4:]}")
