import pytest
import sqlite3
from models.match import get_tous_les_resultats

def test_recuperation_matchs():
    # ID de test (vérifiez qu'il existe dans votre table parieurs)
    parieur_id = 1 
    
    print("\n--- DÉBUT DU TEST DE LA BASE ---")
    try:
        resultats = get_tous_les_resultats(parieur_id)
        print(f"Nombre de matchs récupérés : {len(resultats)}")
        
        for m in resultats:
            print(f"Match ID: {m['id']} | {m['equipe_a']} vs {m['equipe_b']} | Statut: {m['statut']}")
            
        assert isinstance(resultats, list), "La fonction devrait retourner une liste"
    except Exception as e:
        pytest.fail(f"Erreur lors de l'exécution : {e}")

