# 📂 INTERPAM - PROMPT DE RÉFÉRENCE
**Dernière mise à jour :** Janvier 2026
**Statut :** Projet clandestin / Tournoi de pronostics scolaire

## 1. Concept & Vision
InterPam n'est PAS un site de pari d'argent. C'est un **tournoi de pronostiqueurs** au sein du Collège Inter Familia (CIF).
- **Monnaie :** PaMCoin (PMC). 1 PMC = 1 Gourde (monnaie d'entrée, mais virtuelle dans le jeu).
- **Objectif :** Atteindre le TOP 10 du classement (Leaderboard). Les 3 premiers reçoivent une récompense en fin d'année.
- **Vocabulaire OBLIGATOIRE :**
  - NON : "Pari", "Mise", "Gain", "Argent"...
  - OUI : "Pronostic", "Engagement", "Jetons potentiels", "PMC"...

## 2. Règles du Jeu
- **Acquisition :** Les PMC s'obtiennent à l'inscription (selon paiement), en gagnant des pronostics, ou par transfert.
- **Transferts & Alliances :** Les élèves peuvent former des équipes "off-app". Ils transfèrent leurs PMC sur le compte d'un "champion" pour le faire monter dans le classement.
- **Cible :** Élèves et professeurs du CIF.

## 3. Architecture Technique (Flask)
- **Base de données (`data.py`) :**
  - Table `matchs` : Gère les rencontres sportives.
  - Table `options_pari` : Contient les cotes et libellés.
- **Templates HTML :**
  - Utilise Jinja2.
  - Styles CSS externalisés (ne pas changer les IDs/Classes).
  - Structure de base : `base.html` (hérite pour les autres).
- **Fonctionnalités Clés :**
  - Invitations par email (expiration 48h).
  - Rôles : Admin (Organisateur/Direction) et Utilisateur (Joueur).
  - Gestion de tickets (panier de pronostics).
  - Historique des fiches (gagné/perdu/en attente).

## 4. Instructions Spécifiques pour l'IA
- Ne jamais proposer de refonte du code existant sauf si demandé.
- Respecter scrupuleusement les noms de classes CSS et IDs existants.
- Toujours répondre en prenant en compte le caractère "Jeu/Tournoi" et non "Casino/Gambling".
- Le code Python backend gère la logique des cotes et la validation des tickets.
