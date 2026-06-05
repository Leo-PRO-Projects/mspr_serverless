# PROGRESS — Journal d'avancement

> Mis à jour **à chaque étape franchie**. Convention : `[ ]` à faire · `[~]` en cours · `[x]` terminé.
> Dernière mise à jour : **2026-06-05** — *PoC déployé et validé en local (k3d) : 3 fonctions OpenFaaS opérationnelles, cycle complet testé end-to-end*.

---

## Vue d'ensemble des phases

| Phase | Intitulé | Statut | Avancement |
|-------|----------|--------|-----------|
| 0 | Cadrage & documentation | `[~]` en cours | 80 % |
| 1 | Gestion de projet (WBS, Gantt, Kanban, CDC) | `[ ]` | 0 % |
| 2 | Infrastructure Kubernetes + OpenFaaS | `[x]` déployé (k3d) | 100 % |
| 3 | Base de données | `[x]` déployée | 100 % |
| 4 | Développement des fonctions OpenFaaS | `[x]` déployées, testées, images sur GHCR | 100 % |
| 5 | Frontend de démonstration | `[x]` déployé en cluster | 95 % |
| 6 | Intégration, tests & déploiement | `[~]` end-to-end OK | 85 % |
| 7 | Volet multiculturel / inclusion / prestataires | `[ ]` | 0 % |
| 8 | Dossier final + support de soutenance | `[ ]` | 0 % |

---

## Phase 0 — Cadrage & documentation
- [x] Analyse du sujet et de la grille d'évaluation
- [x] Définition de la stack technique (cf. README §3)
- [x] Création de `README.md`, `ARCHITECTURE.md`, `PROGRESS.md`, `LIVRABLES.md`
- [x] Création du squelette de dépôt (docs / infra / functions / frontend)
- [ ] Initialisation du dépôt Git + dépôt distant GitHub
- [ ] Mise en place des outils (Kanboard, canal Slack/Discord)

## Phase 1 — Gestion de projet
- [ ] WBS : découpage en tâches atomiques + dépendances (`docs/gestion-projet/wbs-decoupage.md`)
- [ ] Estimation des charges + affectation des ressources
- [ ] Budget : objectifs coûts global et par ressource (`budget-ressources.md`)
- [ ] Diagramme de Gantt avec jalons (`gantt.md` + export)
- [ ] Mise en place du Kanban (colonnes À faire → En cours → Revue technique → Terminé)
- [ ] Cahier des charges **technique** (objectifs, ressources, outils d'évaluation, mise en œuvre)
- [ ] Cahier des charges **fonctionnel** (objectifs métiers, fonctionnalités, KPIs, dates clés)

## Phase 2 — Infrastructure Kubernetes + OpenFaaS
- [x] Outillage installé : docker, **k3d v5.9**, kubectl v1.34, helm v4.2, faas-cli 0.18
- [x] **Cluster k3d créé** (1 control-plane + 1 worker, `infra/k3d/cluster.yaml`) + correctif kubeconfig Windows
- [x] **OpenFaaS déployé via Helm** (gateway Running, `imagePullPolicy: IfNotPresent`)
- [x] Values Helm + Ingress Traefik + guide local (`infra/k3d/README.md`)
- [x] Script de déploiement automatisé (`scripts/setup-local.sh`)

## Phase 3 — Base de données
- [x] Schéma SQL `users` (`infra/database/schema.sql`)
- [x] StatefulSet PostgreSQL + PVC + Service + ConfigMap d'init (`infra/database/postgres.yaml`)
- [x] **PostgreSQL déployé** (postgres-0 Running) + secrets `cofrap-db` / `db-password` / `fernet-key`
- [x] **Connexion fonction → DB validée** (insertion/lecture chiffrées vérifiées en live)

## Phase 4 — Fonctions OpenFaaS
- [x] `generate-password` (génération 24 car. + chiffrement Fernet + QR + upsert)
- [x] `generate-2fa` (secret TOTP `pyotp` + chiffrement + QR `otpauth://`)
- [x] `authenticate` (vérif. login/mdp/OTP + contrôle 6 mois + flag `expired`)
- [x] `stack.yml` + bascule template **python3-http-debian** (psycopg2 glibc)
- [x] **Images construites** (`scripts/build-images.sh`) + importées dans k3d
- [x] **3 fonctions déployées et Running** (`infra/k8s/functions.yaml`)
- [x] Tests unitaires (`tests/` — **9/9 passés**, DB simulée)
- [x] **Tests end-to-end sur cluster** : password, 2FA, auth OK/KO, expiration 6 mois ✅
- [x] **Push des 4 images sur GHCR** (Mission 6) ✅ — `ghcr.io/leo-pro-projects/cofrap-*:0.1.0`
- [ ] Passer les paquets GHCR en **visibilité publique** (étape UI GitHub)

## Phase 5 — Frontend de démonstration
- [x] Écran authentification (login + mdp + OTP)
- [x] **Création du compte si inexistant** (404 → génération automatique) — conforme au sujet
- [x] **Relance automatique** si compte expiré (status `expired` → régénération) — conforme au sujet
- [x] Écran création explicite (QR mot de passe + QR 2FA)
- [x] **Frontend conteneurisé et déployé dans le cluster** (`infra/k8s/frontend.yaml`, Ingress Traefik)
- [x] Accès validé : `http://cofrap.localhost:8081` (HTTP 200) + appel interne gateway OK
- [ ] Captures d'écran navigateur (pour le dossier)

## Phase 6 — Intégration, tests & déploiement
- [x] Test bout‑en‑bout via gateway : création → 2FA → authentification ✅
- [x] Test du scénario d'expiration (rotation 6 mois) → `expired=1` ✅
- [ ] Captures d'écran de tous les écrans clés (frontend)
- [ ] Vérification robustesse / montée en charge

## Phase 7 — Multiculturel / inclusion / prestataires
- [ ] `multiculturel-communication.md` (communication, anglais, réunions, partage, télétravail, solutions innovantes)
- [ ] `inclusion-handicap.md` (stratégie handicap, ex. déficience visuelle)
- [ ] `gestion-situations-difficiles.md` (scénarios + relais)
- [ ] Tableau de bord prestataires (tableur : SLA, TCD, graphiques)

## Phase 8 — Dossier final + soutenance
- [ ] Rédaction du dossier de rendu (toutes missions + screenshots)
- [ ] Annexes (code fonctions + frontend)
- [ ] Support de présentation (public technique + non‑technique)
- [ ] Préparation de la démonstration live (20 min oral + 30 min entretien)
- [ ] Répétition de la soutenance

---

## Historique des décisions

| Date | Décision | Impact |
|------|----------|--------|
| 2026-06-05 | Stack : Python / K3S / OpenFaaS / PostgreSQL / Fernet / GHCR / Streamlit | Cadre technique du PoC |
| 2026-06-05 | Méthode : Scrum adapté + Kanban (4 rôles, relais) | Cadre de pilotage agile |
| 2026-06-05 | Cluster : **k3d (K3S dans Docker), 100 % local** (pas de VM) | Demande utilisateur : tout sur le PC |
| 2026-06-05 | Template fonctions : **python3-http-debian** (au lieu d'alpine) | psycopg2-binary nécessite glibc |
| 2026-06-05 | Déploiement fonctions via **manifests K8s natifs** | Contourne le blocage "images publiques" d'OpenFaaS CE |

## Journal détaillé

### 2026-06-05
- Initialisation : analyse du sujet + grille, choix de stack, création des 4 documents de pilotage et du squelette de dépôt.
- Choix validés : cluster **K3S (1 control-plane + 1 worker)** ; développement « code d'abord » (Phases 2→4).
- **Infra (Phase 2)** : values Helm OpenFaaS, Ingress Traefik, procédure d'installation complète (`infra/helm/README.md`).
- **BDD (Phase 3)** : schéma SQL + StatefulSet PostgreSQL + ConfigMap d'init + modèle de secrets.
- **Fonctions (Phase 4)** : les 3 handlers Python écrits (chiffrement Fernet, TOTP, QR, expiration 6 mois) + `stack.yml`.
- **Frontend (Phase 5, anticipé)** : app Streamlit de démo (création/auth/expiration).
- ✅ Tests : venv Python 3.13 + dépendances installées, **9 tests unitaires verts** (`pytest tests/`) couvrant génération mot de passe/2FA, QR, chiffrement, auth, et expiration 6 mois.

### 2026-06-05 (suite) — Déploiement local réel
- Bascule architecture en **k3d (local, sans VM)** sur demande utilisateur ; GHCR = `leo-pro-projects`.
- Outillage installé (winget/GitHub) : helm v4.2, k3d v5.9, faas-cli 0.18 (docker + kubectl déjà présents).
- Cluster k3d créé (control-plane + worker), kubeconfig corrigé (host.docker.internal → 127.0.0.1).
- OpenFaaS (Helm) + PostgreSQL (StatefulSet) déployés ; secrets créés.
- Images des 3 fonctions construites (template debian) et importées dans k3d.
- Contournement du blocage OpenFaaS CE (« images publiques ») via Deployments/Services natifs (`infra/k8s/functions.yaml`).
- **Validation end-to-end sur le cluster** : generate-password, generate-2fa, authenticate (OK / mauvais OTP / expiré) → tous conformes.

### 2026-06-05 (suite 2) — Mise en conformité frontend + déploiement cluster
- Frontend réécrit conforme au sujet : **création si inexistant** (404→génération) et **relance auto si expiré**.
- Frontend **conteneurisé** (`frontend/Dockerfile`) et **déployé dans le cluster** (`infra/k8s/frontend.yaml` : Deployment + Service + Ingress Traefik).
- Accès navigateur validé : `http://cofrap.localhost:8081` (HTTP 200) ; appel interne `gateway.openfaas:8080` → fonction → DB → QR OK.
- Scripts mis à jour (build + import + déploiement du frontend) ; `scripts/push-ghcr.sh` prêt pour la livraison GHCR.
- **Reste côté code** : push GHCR (Mission 6, besoin token). Le reste = livrables gestion de projet (Phases 1 & 7).

### 2026-06-05 (suite 3) — Guide d'utilisation
- Ajout de [`docs/GUIDE-UTILISATION.md`](GUIDE-UTILISATION.md) : déploiement, lancement de l'interface,
  parcours utilisateur complet, push GHCR, dépannage et **déroulé de démonstration pour la soutenance**.
- Lié depuis le README ; commande SQL de démo (affichage des données chiffrées) vérifiée.

### 2026-06-05 (suite 4) — Push GHCR réussi (Mission 6)
- Les **4 images** (generate-password, generate-2fa, authenticate, frontend) **poussées sur GHCR**
  (`ghcr.io/leo-pro-projects/cofrap-*:0.1.0`). Login réussi, digests confirmés.
- **Volet technique du sujet désormais 100 % couvert.** Reste : passer les paquets en public (UI GitHub),
  puis les livrables de gestion de projet (Phases 1 & 7).
