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



# 📂 INTERPAM - DOCUMENTATION DE RÉFÉRENCE
**Version :** Janvier 2026
**Type :** Tournoi de Pronostics Scolaire (Clandestin mais éthique)
**Lieu :** Collège Inter Familia (CIF)

---

## 1. 🎯 Concept & Vision
InterPam est un jeu de stratégie et de pronostics sportifs réservé aux élèves et professeurs du CIF.
* **PAS DE JEU D'ARGENT :** On bannit les mots "Pari", "Mise", "Gain", "Argent". On utilise **"Pronostic"**, **"Engagement"**, **"Jetons"**.
* **Monnaie :** PaMCoin (PMC). 1 PMC = 1 Gourde (valeur virtuelle).
* **Objectif :** Atteindre le TOP 10 du Leaderboard. Les 3 premiers reçoivent une récompense financée par les frais de gestion.
* **Alliances :** Les élèves peuvent transférer des PMC à un "Champion" pour le faire monter au classement.

## 2. ⚙️ Règles Métier (Business Logic)

### A. Gestion des Pronostics
* **Résultat :** Basé sur le **Temps Réglementaire (90 min + arrêts de jeu)**. Prolongations/Tirs au but exclus.
* **Limites Dynamiques :**
    * Un ticket est refusé si le gain potentiel dépasse la "Limite du Match".
    * Cette limite est recalculée par l'admin après chaque match selon la cagnotte globale.
* **Matchs Annulés :** Si report > 48h, cote passe à 1.00 (Remboursement).

### B. Gestion des PMC (Économie)
* **Acquisition (Recharge) :**
    * Via Agents Physiques au CIF.
    * Via WhatsApp officiel : **+509 44 81 9817**.
    * *Jamais de dépôt direct dans l'app.*
* **Transferts (P2P) :**
    * Se fait via **Username** (Sensible à la casse !).
    * **Frais :** Une commission est prélevée sur chaque transfert pour alimenter la cagnotte de fin d'année.
    * L'expéditeur voit le montant net que le destinataire recevra.

### C. Règles de Conduite
* **Zone Scolaire :** Interdiction formelle de jouer pendant les heures de cours (Risque de "Banc de touche").
* **Fair-play :** Anti-triche, anti-collusion (sauf alliances déclarées).

## 3. 💻 Architecture Technique

### Backend
* **Langage :** Python 3.
* **Framework :** Flask.
* **Base de données :** SQLite.
* **Fichier clé :** `data.py` (Contient les modèles et la logique DB).
* **Sécurité :** Les mots de passe sont hashés. Pas de données bancaires stockées.

### Frontend
* **Moteur de template :** Jinja2 (`{% extends 'base.html' %}`).
* **Design :**
    * CSS externalisé (Ne jamais changer les noms de classes/IDs).
    * Style "Clean & Dark" (inspiré du code fourni : fonds sombres, accents verts/rouges).
* **Composants clés :**
    * `legal.html` : Accordeons `<details>` pour les règles.
    * `wallet.html` : Système d'onglets JS pour Acquisition/Transfert/Historique.

## 4. 🗄️ Structure des Données (Déduite)

* **Users :** ID, Username (Case sensitive), Solde (PMC), Rôle (Admin/User), Password.
* **Matchs :** Équipes, Cotes, Date, Statut (À venir, En cours, Terminé), Limite d'engagement dynamique.
* **Transactions :** ID, Type (Acquisition, Transfert, Gain Prono, Engagement Prono), Montant, Emetteur, Destinataire, Date, Statut.
* **Pronostics (Tickets) :** ID User, Liste Matchs, Cotes au moment du clic, Mise, Gain Potentiel, Statut.

## 5. 🛠️ Instructions pour l'IA (Moi)
* Toujours vérifier si l'utilisateur demande une info présente dans la base de données (utiliser `Workspace`).
* Ne jamais proposer de refonte visuelle qui casse les IDs existants.
* Maintenir le "Roleplay" du projet clandestin scolaire.
* Si on parle de code, penser "Flask + SQLite + Jinja2".
