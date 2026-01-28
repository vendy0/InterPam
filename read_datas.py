import pandas as pd
from pathlib import Path

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

dossier = Path("./")
for file in dossier.iterdir():
    if not file.is_file():
        continue
    if not file.name.endswith(".csv"):
        continue
    if file.name == "android_metadata.csv":
        continue
    df = pd.read_csv(file.name, sep=";", encoding="utf-8")
    # 2. Exporter vers Excel
    excel_name = file.name.replace(".csv", ".xlsx")
    pres = False
    for verif in dossier.iterdir():
        if verif.name == excel_name:
            pres = True
            break
    if pres == False:
        df.to_excel(excel_name, index=False)
        print(f"📦 Exportation réussie pour {excel_name} !")
    else:
        print(
            f"Fichier {file.name} déjà exporté ! Supprimez ou déplacez d'abord le fichier puis réésayez."
        )
# #
# print(dir(str))
# for file in dossier.iterdir():
#     print(file)
# 