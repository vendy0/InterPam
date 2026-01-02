import google.generativeai as genai
import subprocess
import os

# Configure ton API Key ici (récupère-la sur aistudio.google.com)
genai.configure(api_key="TON_API_KEY")
model = genai.GenerativeModel('gemini-1.5-flash')

def get_diff():
    return subprocess.check_output(["git", "diff", "--cached"]).decode("utf-8")

diff = get_diff()
if not diff:
    print("Rien à commiter (fais un 'git add' d'abord)")
    exit()

prompt = f"Rédige un message de commit court en français basé sur ce diff. Utilise le format 'type(scope): message'. Voici le diff :\n{diff}"
response = model.generate_content(prompt)

print(f"\n--- Message suggéré ---\n{response.text.strip()}\n")

