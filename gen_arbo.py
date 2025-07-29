import os

# Dossiers à exclure
EXCLUS = {'venv', 'env', '__pycache__', '.git', '.idea', 'node_modules', 'migrations', '.vscode'}

# Nom du fichier de sortie
FICHIER_SORTIE = "arborescence.txt"

def afficher_arborescence(racine, fichier, niveau=0):
    try:
        elements = sorted(os.listdir(racine))
    except PermissionError:
        return

    for nom in elements:
        if nom in EXCLUS:
            continue
        chemin = os.path.join(racine, nom)
        indent = "│   " * niveau
        if os.path.isdir(chemin):
            fichier.write(f"{indent}├── {nom}/\n")
            afficher_arborescence(chemin, fichier, niveau + 1)
        elif os.path.isfile(chemin):
            fichier.write(f"{indent}├── {nom}\n")

def main():
    dossier_racine = "."  # Dossier actuel
    with open(FICHIER_SORTIE, "w", encoding="utf-8") as f:
        f.write("Arborescence du projet :\n")
        f.write("├── .\n")
        afficher_arborescence(dossier_racine, f, 1)

    print(f"✅ Fichier '{FICHIER_SORTIE}' généré avec succès.")

if __name__ == "__main__":
    main()
