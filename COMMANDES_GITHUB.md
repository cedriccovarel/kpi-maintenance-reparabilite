# Commandes pour mettre le projet sur GitHub

## 1. Créer un nouveau dépôt sur GitHub

Créer un dépôt nommé par exemple :

```text
kpi-maintenance-reparabilite
```

Choisir de préférence un dépôt privé au début si le projet est encore en phase test.

Ne pas cocher l'ajout automatique d'un README, d'une licence ou d'un .gitignore, car ils sont déjà fournis.

## 2. Initialiser Git en local

Depuis le dossier du projet :

```bash
git init
git add .
git commit -m "Initial commit - prototype KPI maintenance reparabilite carbone"
```

## 3. Brancher le dépôt local au dépôt GitHub

Remplacer l'URL ci-dessous par l'URL réelle du dépôt GitHub :

```bash
git branch -M main
git remote add origin https://github.com/VOTRE-ORGANISATION/kpi-maintenance-reparabilite.git
git push -u origin main
```

## 4. Lancer l'application en local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Sous Windows, remplacer l'activation par :

```bash
.venv\Scripts\activate
```

## 5. Commandes utiles ensuite

Voir les fichiers modifiés :

```bash
git status
```

Ajouter les modifications :

```bash
git add .
git commit -m "Amelioration extraction FDES et rapport"
git push
```
