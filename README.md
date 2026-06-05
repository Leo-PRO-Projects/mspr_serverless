# MSPR TPRE921 — Projet de développement *Serverless* COFRAP

> **Bloc 2 — Manager un projet informatique avec agilité en collaboration avec les parties prenantes**
> Certification *Expert en Informatique et Système d'Information* — RNCP 35584 (Niveau 7) — EPSI/WIS I2 EISI 2025‑2026

---

## 1. Contexte

La **COFRAP** (Compagnie Française de Réalisation d'Applicatifs Professionnels) souhaite refondre le
processus de **création de comptes utilisateurs** de son offre Cloud. Trop de comptes ont été compromis
à cause de mots de passe faibles et de l'absence de 2FA. Le nouveau processus doit :

- générer **automatiquement** un mot de passe robuste (24 caractères : majuscules, minuscules, chiffres, caractères spéciaux) transmis à l'utilisateur via un **QR Code à usage unique** ;
- imposer une **2FA (TOTP / time‑based)** générée dans la foulée pour activer le compte ;
- assurer une **rotation** des mots de passe et tokens 2FA **tous les 6 mois** (compte marqué « expiré » au‑delà).

La solution est un **Proof of Concept (PoC)** *serverless* reposant sur **OpenFaaS Community** + **Kubernetes**,
interagissant avec une base de données. L'implémentation finale sera réalisée par les équipes Infrastructure de la COFRAP.

> ⚠️ Le sujet est avant tout une **MSPR de gestion de projet agile** : le code est un support, mais l'évaluation
> porte majoritairement sur l'organisation, le pilotage, la communication et le multiculturel (cf. [LIVRABLES.md](LIVRABLES.md)).

## 2. Périmètre fonctionnel

| # | Fonction OpenFaaS | Entrée | Sortie | Effet base de données |
|---|-------------------|--------|--------|------------------------|
| 1 | `generate-password` | `username` | QR Code du mot de passe | crée l'utilisateur, stocke le mot de passe **chiffré** + `gendate` |
| 2 | `generate-2fa` | `username` | QR Code `otpauth://` (TOTP) | stocke le secret 2FA **chiffré** |
| 3 | `authenticate` | `username`, `password`, `otp` | OK / KO / **expiré** | vérifie identifiants + ancienneté < 6 mois ; marque `expired=1` si périmé |

Un **frontend de démonstration** orchestre : création de compte → mot de passe (QR) → 2FA (QR) → authentification → renouvellement si expiré.

## 3. Stack technique retenue

| Domaine | Choix | Justification courte |
|---------|-------|----------------------|
| Langage des fonctions | **Python 3.11** | Recommandé par la COFRAP, écosystème riche (`pyotp`, `qrcode`, `cryptography`, drivers SQL) |
| Plateforme *serverless* | **OpenFaaS Community** | Imposé par le sujet ; *scale‑to‑zero*, déploiement léger |
| Orchestration | **Kubernetes via k3d** (K3S dans Docker, 100 % local) | Vrai cluster K3S (control-plane + worker) sans VM ; LoadBalancer (svclb) + Ingress (Traefik) intégrés |
| Déploiement | **Helm** (chart `faas-netes`) | Recommandé, automatise l'installation OpenFaaS |
| Base de données | **PostgreSQL** (StatefulSet K8s) | Robuste, drivers Python matures, table unique |
| Chiffrement | **Fernet** (`cryptography`), clé en *secret* OpenFaaS | Symétrique, simple, conforme au besoin « stocker après chiffrement » |
| 2FA | **TOTP** via `pyotp` | Standard, compatible Google/Microsoft Authenticator |
| QR Code | `qrcode` + `Pillow` | Génération côté fonction |
| Registre d'images | **GHCR** (GitHub Container Registry) | Gratuit, intégré au dépôt Git |
| Frontend | **Streamlit** *(ou Flask + HTML/JS simple)* | Démo rapide, affichage natif des QR codes |

> Le détail et la justification complète figurent dans [ARCHITECTURE.md](ARCHITECTURE.md) et le cahier des charges technique.

## 4. Organisation du dépôt

```
MSPR_Serverless_DEV/
├── README.md                      # Ce fichier — vue d'ensemble (mis à jour à chaque décision structurante)
├── ARCHITECTURE.md                # Architecture technique + organisation de la gestion de projet
├── PROGRESS.md                    # Journal d'avancement (mis à jour à chaque étape franchie)
├── LIVRABLES.md                   # Liste des livrables attendus, mappés au barème
├── docs/
│   ├── cahier-des-charges/        # CDC technique & fonctionnel
│   ├── gestion-projet/            # WBS, Gantt, Kanban, budget, prestataires, multiculturel, inclusion
│   └── dossier-final/            # Dossier de rendu + support de soutenance
├── infra/
│   ├── k3d/                       # Config cluster k3d (local) + guide de déploiement
│   ├── k8s/                       # Manifests Kubernetes (ingress, secrets, fonctions)
│   ├── helm/                      # Values Helm pour OpenFaaS
│   └── database/                  # Schéma SQL + StatefulSet PostgreSQL
├── functions/
│   ├── generate-password/         # Fonction OpenFaaS 1
│   ├── generate-2fa/              # Fonction OpenFaaS 2
│   └── authenticate/             # Fonction OpenFaaS 3
├── frontend/                      # Frontend de démonstration (Streamlit)
├── scripts/                       # setup-local.sh / teardown-local.sh / build-images.sh
├── tests/                         # Tests unitaires des fonctions (DB simulée)
└── stack.yml                      # Définition de la stack OpenFaaS (faas-cli)
```

## 5. Démarrage rapide (déploiement local automatisé)

Tout le PoC se déploie sur le PC (Docker + k3d), sans VM ni cloud :

```bash
bash scripts/setup-local.sh                              # cluster + OpenFaaS + PostgreSQL + fonctions + frontend
# Frontend (déployé dans le cluster, via Traefik) :
#   → http://cofrap.localhost:8081
# Tests directs des fonctions (gateway) :
kubectl -n openfaas port-forward svc/gateway 8080:8080
curl -s -X POST http://127.0.0.1:8080/function/generate-password -d '{"username":"michel.ranu"}'
```

Détail pas-à-pas et explications : [infra/k3d/README.md](infra/k3d/README.md). Suppression : `bash scripts/teardown-local.sh`.

> Les commandes exactes sont documentées au fur et à mesure dans [PROGRESS.md](PROGRESS.md) et le dossier final.

### Tests des fonctions (sans cluster)

Les 3 fonctions sont testables localement avec une base PostgreSQL simulée en mémoire :

```bash
python -m venv .venv
.venv/Scripts/python -m pip install psycopg2-binary qrcode Pillow cryptography pyotp pytest
.venv/Scripts/python -m pytest tests/ -v        # 9 tests : génération, QR, chiffrement, auth, expiration
```

## 6. Équipe & méthode

- **Équipe** (4 apprenants) : **MEYNIER Léo**, **CONTAMIN Alexis**, **LOCATELLI Alexis**, **TRAPPLER Brice** — répartition des rôles (*Scrum Master*, *Lead Dev / DevOps*, *Dev Fonctions*, *Dev Frontend & QA*) dans [ARCHITECTURE.md](ARCHITECTURE.md#rôles).
- **Méthode** : **Scrum adapté + Kanban** (sprints courts, daily meeting, revue technique collective).
- **Outils** : GitHub (code + communication), Kanboard/OpenProject (Kanban), diagramme de Gantt, Slack/Discord.

## 7. Suivi

- 📌 État d'avancement détaillé → [PROGRESS.md](PROGRESS.md)
- 📦 Livrables et conformité barème → [LIVRABLES.md](LIVRABLES.md)
- 🏗️ Décisions d'architecture → [ARCHITECTURE.md](ARCHITECTURE.md)
