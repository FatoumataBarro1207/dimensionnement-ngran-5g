# Application de dimensionnement radio NG-RAN 5G

Application interactive permettant d'automatiser le processus de dimensionnement
radio de la NG-RAN 5G (couverture, capacité, réconciliation), développée en Python
avec Streamlit.

## Contenu du dossier

- `app.py` — code source de l'application
- `requirements.txt` — dépendances Python nécessaires
- `capture_ecran_resultats.png` — exemple d'exécution (scénario urbain dense)

## Installation et exécution

Prérequis : Python 3.9 ou supérieur.

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Lancer l'application
streamlit run app.py
```

L'application s'ouvre automatiquement dans le navigateur à l'adresse
`http://localhost:8501`.

## Fonctionnement

1. Choisir un scénario de zone (Urbain dense / Suburbain / Rural) dans le panneau
   de gauche — les valeurs par défaut se mettent à jour automatiquement.
2. Ajuster les paramètres radio, de trafic et de configuration site à l'aide
   des curseurs.
3. Les résultats se recalculent en temps réel :
   - MAPL et rayon de cellule (dimensionnement couverture)
   - Nombre de sites requis par couverture et par capacité
   - Nombre de sites final et facteur limitant
   - Graphique de sensibilité couverture / capacité selon la densité d'utilisateurs
   - Schéma du maillage hexagonal à l'échelle du rayon calculé
4. Un bouton permet d'exporter une synthèse texte des résultats.

## Modèles utilisés

- Bilan de liaison (link budget) standard
- Propagation : 3GPP TR 38.901 UMa NLOS (urbain dense) et Okumura-Hata
  (suburbain / rural)
- Capacité : efficacité spectrale de Shannon pondérée d'un facteur
  d'implémentation réaliste

## Auteur

Projet réalisé dans le cadre du module Réseaux Mobiles — Dimensionnement et
Planification de la partie radio NG-RAN de la 5G.
