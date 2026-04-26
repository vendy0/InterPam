import pandas as pd
from pathlib import Path
from datetime import datetime

# # 1. Charger le fichier CSV
# # Note : 'sep' peut être ',' ou ';' selon votre source de données
# df = pd.read_csv("parieurs.csv", sep=";", encoding="utf-8")
# print(df)
# # 2. Exporter vers Excel
# df.to_excel("parieurs.xlsx", index=False)
# print("Exportation réussie !")
##
# pd.set_option("display.max_columns", 4)
# pd.set_option("display.max_colwidth", None)
# pd.set_option("display.width", 0)
# pd.set_option("display.max_rows", None)
#
# df = pd.read_csv("parieurs.csv", sep=";", encoding="utf-8")
# print(df)


def main_to_excel(dossier, path_csv, date_export):
	if not path_csv.exists() or not dossier.exists():
		print("Dossier introuvable !")
		return
	chemin_excel = dossier.joinpath("EXCEL")
	chemin_excel.mkdir(parents=True, exist_ok=True)

	for file in path_csv.glob("*.csv"):
		if file.name == "android_metadata.csv":
			continue
		try:
			df = pd.read_csv(file, sep=";", encoding="utf-8")
			# 2. Exporter vers Excel
			excel_name = f"{file.stem}_{date_export}.xlsx"
			chemin_final = chemin_excel / excel_name
			if not chemin_final.exists():
				df.to_excel(chemin_final, index=False)
				print(f"📦 Conversion réussie pour {excel_name} !")
			else:
				print(
					f"Fichier {file.name} déjà exporté ! Supprimez ou déplacez d'abord le fichier puis réésayez."
				)
		except Exception as e:
			print(f"Erreur sur : {file.name} !   {e}")
	print("FIN DE LA CONVERSION".center(50, "_"), "\n")


# #
# print(dir(str))
# for file in dossier.iterdir():
#     print(file)
#
