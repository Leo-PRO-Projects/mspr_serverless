# LIVRABLES — MSPR TPRE921 (Serverless COFRAP)

Liste exhaustive des livrables attendus, **mappés au barème** (grille Bloc 2) et aux missions du sujet.
Statut : `[ ]` à produire · `[~]` en cours · `[x]` produit.

---

## 1. Livrable principal — Dossier de rendu final

Document unique reprenant l'ensemble du projet (Mission 8 + section V du sujet) :

- [ ] **L1.1** — Présentation & justification des choix : langage, technologies (BDD, frontend), solution K8s / cloud / baremetal
- [ ] **L1.2** — Diagramme de **Gantt** (tâches + planning prévisionnel + jalons)
- [ ] **L1.3** — Tableau **Kanban** (ou équivalent) illustrant le suivi des tâches
- [ ] **L1.4** — Mesures pour un **environnement inclusif** (exemple concret : accueil handicap visuel)
- [ ] **L1.5** — Description de l'**architecture retenue** (cluster/K3S/minikube/cloud), choix & difficultés rencontrées
- [ ] **L1.6** — Étapes de **déploiement OpenFaaS** (Helm, Ingress, LoadBalancer) + paramètres principaux
- [ ] **L1.7** — Présentation des **fonctions développées** (rôle, entrées/sorties, liens BDD & sécurité)
- [ ] **L1.8** — Description de l'**architecture globale** (frontend ↔ OpenFaaS ↔ BDD)
- [ ] **L1.9** — **Captures d'écran** + explications : création compte, mot de passe + QR, secret TOTP/2FA, authentification, renouvellement
- [ ] **L1.10** — **Annexes** : code source des fonctions OpenFaaS + du frontend

## 2. Livrables de gestion de projet (Bloc 2 — cœur du barème)

- [ ] **L2.1** — **WBS / découpage** du projet en tâches atomiques + enchaînement + ressources affectées
- [ ] **L2.2** — **Objectifs délais** : dates de début, lancement, jalons
- [ ] **L2.3** — **Objectifs coûts** : budget global et par ressource
- [ ] **L2.4** — **Cahier des charges technique** (objectifs, ressources planifiées, outils d'évaluation, mise en œuvre)
- [ ] **L2.5** — **Cahier des charges fonctionnel** (objectifs métiers, fonctionnalités, indicateurs de performance, dates clés des livrables)
- [ ] **L2.6** — **Indicateurs de suivi** quantitatifs & qualitatifs (productivité, performance, qualité)
- [ ] **L2.7** — Preuve d'usage d'un **outil de centralisation des tâches** (Kanboard/Jira/Trello) + **outil de communication** (Slack/GitHub)
- [ ] **L2.8** — Organisation des **réunions de suivi** (Daily Meeting, revue technique)
- [ ] **L2.9** — **Tableau de bord prestataires** (tableur) : coordonnées, nature, **SLA**, dates/durée, indicateurs + **pénalités**, fréquence de suivi — avec **calculs complexes, tableaux croisés dynamiques, graphiques**

## 3. Livrables « équipe & multiculturel » (Bloc 2)

- [ ] **L3.1** — Plan de **conduite d'équipe agile** : attribution des rôles, scénarios agiles, **personne relais**
- [ ] **L3.2** — Démonstration de **communication bienveillante** : écoute active, reformulation, référence culturelle, **traduction en anglais**
- [ ] **L3.3** — **3 solutions innovantes** minimum (serious game à distance, temps informels, webinaires culturels)
- [ ] **L3.4** — **Processus de communication inclusif** (outil collaboratif + fil de discussion check‑in/check‑out)
- [ ] **L3.5** — **Séquence d'animation de réunion à distance** (classe inversée + outils : Padlet/Kahoot/Klaxoon)
- [ ] **L3.6** — **Stratégie de partage d'information** (outils + schémas d'utilisation + présentation visuelle)
- [ ] **L3.7** — **Plan d'accompagnement du télétravail** (besoins/contraintes, points journaliers/hebdo, décalages horaires)
- [ ] **L3.8** — **Stratégie d'accueil du handicap** (en lien avec le référent handicap)

## 4. Livrables techniques (artefacts de code & infra)

- [x] **L4.1** — `infra/database/schema.sql` + manifests StatefulSet PostgreSQL
- [x] **L4.2** — `infra/helm/` + `infra/k3d/` : values + procédure d'installation OpenFaaS (local k3d)
- [x] **L4.3** — `infra/k8s/` : Ingress, secrets (templates), manifests fonctions & frontend
- [x] **L4.4** — `functions/generate-password/` (code + handler + requirements)
- [x] **L4.5** — `functions/generate-2fa/`
- [x] **L4.6** — `functions/authenticate/`
- [x] **L4.7** — `stack.yml` (définition faas-cli des 3 fonctions + images GHCR)
- [ ] **L4.8** — Images de conteneurs **publiées sur GHCR** *(script prêt, besoin token `write:packages`)*
- [x] **L4.9** — `frontend/` : application de démonstration **déployée dans le cluster**

## 5. Livrables de soutenance

- [ ] **L5.1** — **Support de présentation** (20 min) adapté à un public **technique ET non‑technique**
- [ ] **L5.2** — **Démonstration live** de l'applicatif fonctionnel
- [ ] **L5.3** — Préparation à l'**entretien collectif** (30 min) — justification & valorisation du travail

---

## Synthèse de conformité au barème

L'évaluation repose sur **3 piliers** (section V du sujet) :
1. **Qualité du travail** réalisé pendant le projet → livrables §2, §3, §4 ;
2. **Pertinence & exhaustivité des livrables** → dossier final §1 ;
3. **Capacité à présenter / justifier / valoriser** en soutenance → §5.

> ⚠️ Rappel : le jury (2 évaluateurs externes) ne connaît pas l'équipe. La soutenance doit **démontrer
> explicitement** chaque compétence de la grille (cf. tableau de traçabilité dans [ARCHITECTURE.md](ARCHITECTURE.md#traçabilité-barème--artefacts)).
