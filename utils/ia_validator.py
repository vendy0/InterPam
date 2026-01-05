import os
import requests
import json
import re
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

def analyser_et_comparer(sms_brut, montant_attendu, id_attendu, tel_attendu):
	if not API_KEY:
		return {"verdict": "ERREUR", "commentaire": "Clé API non trouvée dans le .env"}

	# Configuration du modèle Gemini 2.0 Flash
	model_name = "gemini-2.0-flash" 
	url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={API_KEY}"
	
	prompt = f"""
	Tu es un assistant de sécurité pour une plateforme de paiement.
	Analyse ce SMS MonCash : "{sms_brut}"
	Vérifie s'il correspond à :
	- Montant : {montant_attendu} HTG
	- ID Transaction : {id_attendu}
	- Téléphone : {tel_attendu}

	Réponds UNIQUEMENT en JSON :
	{{
	  "verdict": "VALIDE" ou "FRAUDE",
	  "confiance": 0-100,
	  "commentaire": "explication courte"
	}}
	"""

	payload = {
		"contents": [{
			"parts": [{"text": prompt}]
		}]
	}
	try:
		response = requests.post(url, json=payload, timeout=10)
		data = response.json()

		if 'error' in data:
			if data['error'].get('code') == 429:
				return {"verdict": "ERREUR", "commentaire": "Trop de requêtes. Quota épuisé."}
			return {"verdict": "ERREUR", "commentaire": f"Google: {data['error']['message']}"}
		
		# ... reste du code pour extraire les tokens et le verdict


		# Extraction du texte de la réponse
		texte_reponse = data['candidates'][0]['content']['parts'][0]['text']
		
		# Nettoyage et extraction du JSON via Regex
		match = re.search(r'\{.*\}', texte_reponse, re.DOTALL)
		if match:
			return json.loads(match.group())
		else:
			return json.loads(texte_reponse.strip())
			
	except Exception as e:
		return {"verdict": "ERREUR", "commentaire": f"Erreur technique: {str(e)}"}
