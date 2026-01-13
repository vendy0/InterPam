from models.admin import ajouter_match, ajouter_option

#
# from data import ajouter_column
# from data import update
# from database.setup import create
# create()
match_id = ajouter_match("S2", "S1", "Ce soir", "foot")
if match_id:
	ajouter_option("Victoire S1", 2.4, "Victoire_equipe", match_id)
	ajouter_option("Null", 1.2, "Victoire_equipe", match_id)
	ajouter_option("Victoire S2", 0.2, "Victoire_equipe", match_id)
	ajouter_option(" < 3", 1.1, "Nombre_de_but", match_id)
	ajouter_option(" > 3, < 7", 2.0, "Nombre_de_but", match_id)
	ajouter_option("> 7", 5.0, "Nombre_de_but", match_id)
#
match_id = ajouter_match("9e", "S1", "Ce soir", "basket")
if match_id:
	ajouter_option("Victoire S1", 2.4, "Victoire_equipe", match_id)
	ajouter_option("Null", 1.2, "Victoire_equipe", match_id)
	ajouter_option("Victoire S2", 0.2, "Victoire_equipe", match_id)
	ajouter_option(" < 3", 1.1, "Nombre_de_but", match_id)
	ajouter_option(" > 3, < 7", 2.0, "Nombre_de_but", match_id)
	ajouter_option("> 7", 5.0, "Nombre_de_but", match_id)

# ajouter_column()

# update()
