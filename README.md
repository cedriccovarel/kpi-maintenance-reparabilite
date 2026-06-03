# KPI Maintenance, Réparabilité et Carbone

Prototype d'application pour tester des indicateurs de maintenance, réparabilité et impact carbone à partir de documents PDF bâtiment.

L'application permet de déposer plusieurs types de documents, d'extraire automatiquement certaines informations et de générer un rapport même si le dossier est incomplet.

## Objectif du prototype

L'objectif est de démontrer qu'il est possible de comparer des matériaux, équipements ou choix techniques selon :

- leur impact carbone annualisé ;
- leur durée de vie de référence ;
- leur potentiel de réparation ou de remplacement partiel ;
- leur potentiel d'évitement carbone et financier.

Ce prototype n'est pas un outil réglementaire. Il sert à tester une méthode, identifier les données disponibles et montrer l'intérêt d'un indicateur simple.

## Indicateurs calculés

### ICA - Impact Carbone Annualisé

```text
ICA = impact carbone total / durée de vie de référence
```

Lecture : plus l'ICA est faible, plus le produit ou équipement est performant sur sa durée de vie.

### PER - Potentiel d'Évitement par Réparation

```text
PER carbone = impact carbone total x (1 - coefficient de remplacement)
PER financier = coût unitaire x (1 - coefficient de remplacement)
```

Lecture : plus le PER est élevé, plus la solution permet potentiellement d'éviter du carbone ou du coût grâce à une réparation ou un remplacement partiel.

## Documents prévus dans l'application

L'interface prévoit 5 zones de dépôt PDF :

1. CCTP / DPGF / descriptif technique
2. FDES / PEP / fiches environnementales
3. Notices d'entretien / maintenance fabricant
4. DOE / historique GMAO / exploitation
5. Devis / variantes / offres entreprises

Le rapport peut être généré même si certains documents sont absents. Les documents manquants sont signalés dans le rapport.

## Installation locale

Cloner le dépôt :

```bash
git clone https://github.com/VOTRE-ORGANISATION/kpi-maintenance-reparabilite.git
cd kpi-maintenance-reparabilite
```

Créer un environnement Python :

```bash
python -m venv .venv
```

Activer l'environnement :

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

Installer les dépendances :

```bash
pip install -r requirements.txt
```

Lancer l'application :

```bash
streamlit run app.py
```

## Structure du dépôt

```text
kpi-maintenance-reparabilite/
├── app.py
├── requirements.txt
├── README.md
├── METHODE_KPI.md
├── LICENSE
└── .gitignore
```

## Limites connues

- Les PDF scannés peuvent nécessiter un OCR.
- L'extraction dépend de la qualité du texte PDF.
- Les FDES/PEP ne sont pas toujours homogènes dans la présentation des modules ACV.
- La reconnaissance des familles d'ouvrages repose sur une bibliothèque de mots-clés.
- Les coefficients de remplacement sont simplifiés pour la phase test.
- Les résultats doivent être relus avant toute utilisation contractuelle ou réglementaire.

## Prochaines évolutions possibles

- Ajouter OCR pour PDF scannés.
- Ajouter un export Excel.
- Améliorer la bibliothèque de familles d'ouvrages.
- Ajouter une comparaison multi-variantes.
- Rapprocher automatiquement les données avec des références FDES/PEP.
- Ajouter une gestion de projets.
- Ajouter un niveau de confiance plus détaillé.
