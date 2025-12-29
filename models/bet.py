



def valider_option_gagnante(option_id, match_id):
    """
    Met l'option à 1 (gagné) et les autres options de la même
    catégorie pour ce match à 2 (perdu).
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            # 1. Récupérer la catégorie de l'option choisie
            cur.execute("SELECT categorie FROM options WHERE id = ?", (option_id,))
            res = cur.fetchone()
            if not res:
                return False
            categorie = res[0]

            # 2. Mettre toutes les options de cette catégorie pour ce match à 2 (perdu)
            cur.execute(
                """
                UPDATE options SET winner = 2 
                WHERE match_id = ? AND categorie = ?
            """,
                (match_id, categorie),
            )

            # 3. Mettre l'option spécifique à 1 (gagné)
            cur.execute("UPDATE options SET winner = 1 WHERE id = ?", (option_id,))

            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Erreur validation : {e}")
        return False


def fermer_match_officiellement(match_id):
    """Change le statut du match pour qu'il ne soit plus modifiable."""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE matchs SET statut = 'terminé' WHERE id = ?", (match_id,)
            )
            conn.commit()
            return True
    except sqlite3.Error as e:
        print(f"Erreur fermeture match : {e}")
        return False