# Méthode de calcul - Prototype

## Données extraites

L'application tente d'extraire :

- impact carbone en kgCO2e ;
- durée de vie de référence en années ;
- coût unitaire en euros ;
- familles d'ouvrages reconnues par mots-clés ;
- coefficient de remplacement associé à la famille.

## ICA

L'ICA correspond à l'impact carbone annualisé :

ICA = impact carbone total / durée de vie

Un ICA faible indique qu'un produit est intéressant sur sa durée d'usage, même s'il peut être plus impactant à l'installation.

## PER

Le PER mesure le potentiel d'évitement par réparation ou remplacement partiel :

PER carbone = impact carbone total x (1 - coefficient de remplacement)

PER financier = coût unitaire x (1 - coefficient de remplacement)

Exemples de coefficients :

- 0,10 : remplacement localisé faible
- 0,25 : remplacement partiel moyen
- 0,50 : intervention partielle lourde
- 1,00 : remplacement complet

## Niveau de confiance

Le prototype distingue :

- valeur extraite automatiquement ;
- valeur de secours ;
- valeur non trouvée.

Ce point est important pour montrer l'efficacité de l'approche sans masquer les limites des données disponibles.
