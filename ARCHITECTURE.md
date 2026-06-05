# ARCHITECTURE — MSPR TPRE921 (Serverless COFRAP)

Ce document décrit **deux dimensions** :
1. l'**architecture technique** de la solution (le *quoi* et le *comment* du code) ;
2. l'**organisation de la gestion de projet** (méthode agile, outils, gouvernance) — au cœur du barème du Bloc 2.

---

# PARTIE A — Architecture technique

## A.1 Vue d'ensemble

```
                          ┌──────────────────────────────────────────────┐
                          │              Cluster Kubernetes (K3S)          │
                          │                                                │
  Utilisateur            │   ┌────────────┐      ┌──────────────────────┐ │
   (navigateur)          │   │  Ingress    │      │     OpenFaaS         │ │
       │                 │   │  (Traefik)  │      │  (gateway + faas-    │ │
       ▼                 │   └─────┬──────┘      │   netes, scale-to-0)  │ │
  ┌──────────┐   HTTP    │         │              │                      │ │
  │ Frontend │──────────▶│         ▼              │  ┌────────────────┐  │ │
  │ (démo)   │           │   ┌────────────┐  call │  │ generate-password│ │ │
  └──────────┘◀──────────│   │  Frontend   │─────▶│  ├────────────────┤  │ │
       ▲      QR / JSON  │   │  (Pod)      │      │  │ generate-2fa    │  │ │
       │                 │   └────────────┘      │  ├────────────────┤  │ │
       │                 │                        │  │ authenticate    │  │ │
       │                 │                        │  └───────┬────────┘  │ │
       │                 │                        └──────────┼───────────┘ │
       │                 │                                   │ SQL          │
       │                 │                        ┌──────────▼───────────┐ │
       │                 │                        │  PostgreSQL          │ │
       │                 │                        │  (StatefulSet + PVC) │ │
       │                 │                        └──────────────────────┘ │
       │                 └──────────────────────────────────────────────┘
       │
   Secrets OpenFaaS : clé Fernet, identifiants base de données
```

**Flux applicatif** : `Frontend ↔ OpenFaaS (fonctions) ↔ PostgreSQL`. Les fonctions sont sans état ; tout
état persiste en base. Les secrets ne transitent jamais en clair : chiffrement **Fernet** avant stockage.

## A.2 Schéma de la base de données

Table unique `users` (conforme à l'exemple du sujet) :

| Colonne    | Type                | Description |
|------------|---------------------|-------------|
| `id`       | `SERIAL PRIMARY KEY`| Identifiant interne |
| `username` | `VARCHAR UNIQUE`    | Login utilisateur (ex. `michel.ranu`) |
| `password` | `TEXT`              | Mot de passe **chiffré (Fernet)** |
| `mfa`      | `TEXT`              | Secret TOTP **chiffré (Fernet)** |
| `gendate`  | `BIGINT`            | Timestamp Unix de dernière génération (base du calcul d'expiration 6 mois) |
| `expired`  | `SMALLINT DEFAULT 0`| `0` = actif, `1` = expiré |

> Règle d'expiration : `now - gendate > 6 mois (≈ 15 552 000 s)` ⇒ `expired = 1` et relance du processus.

## A.3 Fonctions OpenFaaS (Python 3.11)

| Fonction | Logique | Librairies clés | Secrets utilisés |
|----------|---------|-----------------|------------------|
| **generate-password** | génère 24 car. (4 classes), crée l'utilisateur si absent, chiffre + stocke le mot de passe, met à jour `gendate`, retourne le **QR Code** (image base64 ou PNG) | `secrets`, `qrcode`, `cryptography`, `psycopg2` | `fernet-key`, `db-*` |
| **generate-2fa** | génère un secret TOTP, chiffre + stocke dans `mfa`, retourne un **QR Code `otpauth://`** scannable par une app d'authentification | `pyotp`, `qrcode`, `cryptography`, `psycopg2` | `fernet-key`, `db-*` |
| **authenticate** | vérifie `username`+`password`+`otp`, contrôle `gendate < 6 mois` ; si périmé → `expired=1` + réponse « relancer création » | `pyotp`, `cryptography`, `psycopg2` | `fernet-key`, `db-*` |

**Sécurité** : la clé Fernet et les identifiants PostgreSQL sont injectés via **OpenFaaS secrets**
(`faas-cli secret create`), montés dans `/var/openfaas/secrets/`. Aucune donnée sensible en clair en base,
ni dans le code, ni dans les images.

## A.4 Frontend de démonstration

Rôle **strictement limité à la démo** (le sujet insiste sur la simplicité), avec le flux exact attendu :
- **authentification** (login + mot de passe + code TOTP → `authenticate`) ;
- **création du compte s'il n'existe pas** (réponse 404 → `generate-password` puis `generate-2fa`, 2 QR codes) ;
- **relance automatique** de la génération si le compte est **expiré** (réponse `expired` → régénération).

Techno : **Streamlit** (affichage natif des QR, zéro build front). Le frontend est **conteneurisé
et déployé dans le cluster** (`infra/k8s/frontend.yaml` : Deployment + Service + Ingress Traefik),
accessible sur `http://cofrap.localhost:8081` ; il appelle la gateway via `http://gateway.openfaas:8080`.

## A.5 Infrastructure & déploiement — **100 % local (k3d)**

Choix retenu : tout tourne sur le PC via **Docker + k3d** (K3S dans des conteneurs), sans VM ni cloud.

1. **Cluster** : `k3d cluster create` → 1 nœud *server* (control‑plane) + 1 nœud *agent* (worker), image `rancher/k3s`. Traefik (Ingress) et svclb (LoadBalancer) fournis par K3S. Config : `infra/k3d/cluster.yaml`.
2. **PostgreSQL** : StatefulSet + PVC + Service headless + ConfigMap d'init (`infra/database/postgres.yaml`).
3. **OpenFaaS** : `helm upgrade --install openfaas openfaas/openfaas` (namespaces `openfaas` + `openfaas-fn`), values `infra/helm/values-openfaas.yaml` (`imagePullPolicy: IfNotPresent` pour utiliser les images importées localement).
4. **Images** : build via `scripts/build-images.sh` (contourne un bug de chemin Windows de `faas-cli build`) puis `k3d image import` → injectées dans le cluster **sans registre externe**.
5. **Déploiement des fonctions** : manifests Kubernetes natifs (`infra/k8s/functions.yaml`) avec label `faas_function`, reconnus et routés par la gateway.
6. **Secrets** : `fernet-key` et `db-password` créés en *secrets Kubernetes*, montés dans `/var/openfaas/secrets/`.

> **Contournement OpenFaaS CE** : la Community Edition refuse les images non publiques via son API
> de déploiement. Pour rester 100 % local, on déploie les fonctions en Deployments/Services natifs
> (voie locale). La voie « livraison » standard reste `faas-cli up -f stack.yml` avec push **GHCR public**
> (`stack.yml`, registre `ghcr.io/leo-pro-projects`). Détails : `infra/k3d/README.md`.

> Déploiement automatisé de bout en bout : `bash scripts/setup-local.sh`.

## A.6 Choix techniques — synthèse justificative (pour le dossier final)

- **Python** : recommandé COFRAP + librairies prêtes à l'emploi (crypto, TOTP, QR, SQL).
- **K3S** : recommandé par le sujet en baremetal, LoadBalancer + Ingress inclus → moins de plomberie.
- **PostgreSQL** : fiabilité, table unique suffisante, intégration K8s simple via StatefulSet.
- **Fernet** : chiffrement symétrique authentifié, suffisant pour un PoC, clé gérée par secret.
- **GHCR** : registre gratuit lié au dépôt, pas de compte tiers supplémentaire.

---

# PARTIE B — Organisation de la gestion de projet (Bloc 2)

> C'est le cœur de l'évaluation. Cette partie structure **comment** l'équipe pilote le projet.

## B.1 Méthode agile retenue

**Scrum adapté + Kanban** :
- **Scrum** pour le rythme : sprints courts sur les 19 h de préparation, *Sprint Planning* initial, *Daily Meeting*, *Sprint Review* + *Rétrospective*.
- **Kanban** pour le flux des tâches : colonnes **À faire → En cours → Revue technique → Terminé** (conforme au sujet, la *Revue technique* se fait collectivement).

*Justification* : le PoC est court, l'équipe réduite (4) et le périmètre technique exploratoire (Kubernetes/OpenFaaS) → un cadre Scrum léger combiné à un flux Kanban visuel maximise l'adaptabilité et la visibilité, conformément aux principes d'agilité (adaptation, flexibilité, amélioration continue).

## B.2 Rôles de l'équipe {#rôles}

| Rôle | Membre *(à confirmer en équipe)* | Responsabilités principales | Suppléance (relais) |
|------|------|------------------------------|------------------------------|
| **Scrum Master / Chef de projet** | MEYNIER Léo | animation agile, Gantt, Kanban, suivi KPIs, pilotage prestataires, relation jury/COFRAP | Lead Dev |
| **Lead Dev / DevOps** | CONTAMIN Alexis | cluster k3d, Helm, OpenFaaS, secrets, base de données | Scrum Master |
| **Dev Fonctions** | LOCATELLI Alexis | développement des 3 fonctions OpenFaaS + chiffrement/2FA | Dev Frontend |
| **Dev Frontend & QA** | TRAPPLER Brice | frontend de démo, tests d'intégration, captures d'écran, dossier | Dev Fonctions |

> Répartition des rôles proposée — à valider/ajuster collectivement lors du *Sprint Planning*.

> **Personne relais** : chaque rôle dispose d'un suppléant identifié pour absorber une absence/urgence (exigence du barème).

## B.3 Outils

| Besoin | Outil retenu | Alternative |
|--------|-------------|-------------|
| Code & versioning | **GitHub** | GitLab |
| Communication équipe | **Slack / Discord** + GitHub (issues, PR) | Teams |
| Centralisation des tâches / Kanban | **Kanboard** (open source) | OpenProject, Redmine, Trello, Jira |
| Planification / Gantt | **GanttProject** ou tableur | MS Project, OpenProject |
| Réunions à distance | **Teams / Zoom / Google Meet** | Jitsi |
| Animation interactive | **Klaxoon / Kahoot / Padlet** | Miro |
| Tableau de bord prestataires | **Tableur** (calculs, TCD, graphiques) | Excel / Google Sheets / LibreOffice Calc |

## B.4 Découpage projet (WBS) et planning

Le découpage en tâches atomiques, l'estimation, l'enchaînement et l'affectation des ressources sont
détaillés dans :
- `docs/gestion-projet/wbs-decoupage.md` — découpage en lots/tâches + dépendances + ressources + coûts ;
- `docs/gestion-projet/gantt.md` — diagramme de Gantt (jalons, dates début/fin, chemin) ;
- `docs/gestion-projet/kanban.md` — organisation et règles du Kanban ;
- `docs/gestion-projet/budget-ressources.md` — objectifs coûts (global + par ressource) et délais.

## B.5 Suivi de performance (KPIs)

Indicateurs **quantitatifs** : vélocité (tâches/sprint), nombre de tâches Terminé vs Planifié, temps réel vs estimé, taux de bugs, couverture des fonctions livrées.
Indicateurs **qualitatifs** : qualité des fonctionnalités (revue technique), satisfaction équipe (rétrospective), respect des standards de code.
Cadence de suivi : **Daily Meeting** (15 min) + revue de sprint.

## B.6 Pilotage des prestataires extérieurs

Tableau de bord (tableur) listant : coordonnées, nature de prestation, **SLA**, dates/durée contrat,
indicateurs de performance + **pénalités** cohérentes avec les SLA, fréquence de suivi.
Construit avec **calculs complexes, tableaux croisés dynamiques et graphiques** → `docs/gestion-projet/prestataires-tableau-de-bord.md` (spéc.) puis fichier tableur dans le dossier final.

> Exemples de prestataires simulés : fournisseur cloud/hébergeur du cluster, fournisseur de registre d'images, support OpenFaaS Pro.

## B.7 Dimension multiculturelle & inclusion

Contexte imposé : **environnement multiculturel** + **accueil du handicap**. Documenté dans :
- `docs/gestion-projet/multiculturel-communication.md` — modes de communication selon cultures/langues, écoute active, reformulation, références culturelles, traduction **anglais** ; solutions innovantes (serious games à distance, temps informels, webinaires culturels) ; processus de communication inclusif (check‑in/check‑out) ; animation de réunions à distance (classe inversée, outils interactifs) ; partage d'information ; accompagnement du télétravail (décalages horaires, équilibre pro/perso).
- `docs/gestion-projet/inclusion-handicap.md` — stratégie d'accueil du handicap (ex. déficience visuelle : lecteurs d'écran, contrastes, adaptation de la charge), en lien avec le référent handicap.

## B.8 Gestion des situations difficiles

Scénarios agiles documentés (ex. panne de cluster, départ d'un membre, changement de priorité) avec
plusieurs réponses possibles, prise en compte des contraintes de temps et des événements exceptionnels,
et activation de la **personne relais** → `docs/gestion-projet/gestion-situations-difficiles.md`.

---

## Traçabilité barème → artefacts

| Compétence (grille Bloc 2) | Artefact projet |
|----------------------------|-----------------|
| Découpage projet / tâches / ressources / délais / coûts | `wbs-decoupage.md`, `gantt.md`, `budget-ressources.md` |
| CDC technique & fonctionnel | `docs/cahier-des-charges/` |
| Gérer un projet agile (méthode + outils com + centralisation tâches) | §B.1, §B.3, Kanban, GitHub |
| Tableaux de bord de suivi (Gantt, KPIs, planif, daily) | `gantt.md`, `kanban.md`, §B.5 |
| Pilotage prestataires (tableur, SLA, TCD, graphiques) | `prestataires-tableau-de-bord.md` |
| Conduite d'équipe agile / situations difficiles / relais | `gestion-situations-difficiles.md`, §B.2 |
| Communication multiculturelle + anglais | `multiculturel-communication.md` |
| Solutions innovantes interactions | `multiculturel-communication.md` |
| Processus communication inclusif (check‑in/out) | `multiculturel-communication.md` |
| Animation réunions à distance | `multiculturel-communication.md` |
| Partage d'information à distance | `multiculturel-communication.md` |
| Accompagnement télétravail | `multiculturel-communication.md` |
| Stratégie handicap | `inclusion-handicap.md` |
