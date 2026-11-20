# Installation

> Installer MagicTable et le lancer, sous Linux depuis les sources ou sous Windows avec l'exécutable.

## À installer

- git
- python
- PySide6
- networkx
- certifi
- fpdf2

## Windows : l'exécutable

1. Télécharger `MagicTable.exe` depuis la dernière release GitHub du projet.
2. Le placer dans un dossier à soi (par exemple `Documents\MagicTable`) et le lancer.

Les données sont créées dans `%APPDATA%\MagicTable\data`. Les mises à jour se font ensuite depuis
l'application (Paramètres › Mise à jour).

## Linux : depuis les sources

### 1. Les paquets du système

```bash
sudo pacman -S git python
```

### 2. Le code

```bash
git clone https://github.com/MartinFraysse/MagicTable.git
cd MagicTable
```

### 3. L'environnement Python

Les dépendances s'installent dans un environnement virtuel propre au projet (`.venv`), jamais dans le Python du système :

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Lancer

```bash
python src/app.py
```

Les données sont lues et écrites dans `src/data/`.

## Vérifier

- La fenêtre MagicTable s'ouvre sur le **Dashboard**, avec la barre de navigation à gauche.
- L'onglet **Tournois** affiche la zone « À venir » et la zone de lancement.
- Après une mise à jour du code, relancer `pip install -r requirements.txt` : une dépendance a pu s'ajouter.

En cas d'erreur au lancement, voir la page Dépannage du chapitre Exploitation.
