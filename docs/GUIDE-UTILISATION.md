# Guide d'utilisation & de démonstration — PoC Serverless COFRAP

Ce guide explique **pas à pas** comment déployer, utiliser et présenter le projet.
Il est pensé pour la **soutenance MSPR** : déploiement à partir de zéro, lancement de l'interface,
parcours utilisateur, et déroulé de démonstration devant le jury.

> ℹ️ Toutes les commandes sont données pour **Git Bash** (MINGW64) sous Windows, depuis la racine
> du projet `C:\MSPR_Serverless_DEV`. Le cluster Kubernetes tourne **en local** dans Docker (k3d).

---

## Sommaire
1. [Architecture en une image](#1-architecture-en-une-image)
2. [Prérequis](#2-prérequis)
3. [Déploiement complet (une commande)](#3-déploiement-complet-une-commande)
4. [Lancer l'interface web](#4-lancer-linterface-web)
5. [Parcours utilisateur (la démo)](#5-parcours-utilisateur-la-démo)
6. [Publier les images sur GHCR (Mission 6)](#6-publier-les-images-sur-ghcr-mission-6)
7. [Vérifier que tout fonctionne](#7-vérifier-que-tout-fonctionne)
8. [Tests automatisés](#8-tests-automatisés)
9. [Dépannage](#9-dépannage)
10. [Arrêter / nettoyer](#10-arrêter--nettoyer)
11. [Déroulé conseillé pour la soutenance](#11-déroulé-conseillé-pour-la-soutenance)

---

## 1. Architecture en une image

```
   Navigateur                  Cluster Kubernetes (k3d, dans Docker)
   (vous)                ┌───────────────────────────────────────────────┐
      │                  │  Ingress Traefik                               │
      │ http://cofrap.   │      │                                         │
      │   localhost:8081 │      ▼                                         │
      ├─────────────────►│  Frontend (Streamlit)                          │
      │                  │      │  http://gateway.openfaas:8080            │
      │                  │      ▼                                         │
      │                  │  Gateway OpenFaaS ──► generate-password ─┐     │
      │                  │                    ├─► generate-2fa ──────┤     │
      │                  │                    └─► authenticate ──────┤     │
      │                  │                                          ▼     │
      │                  │                              PostgreSQL (table users) │
      │                  └───────────────────────────────────────────────┘
      ▲                          Secrets : clé Fernet, mot de passe DB
      └── QR codes (mot de passe + 2FA), réponses JSON
```

**Flux** : `Frontend ↔ OpenFaaS (3 fonctions) ↔ PostgreSQL`. Mots de passe et secrets 2FA sont
**chiffrés (Fernet)** avant stockage. Détails dans [ARCHITECTURE.md](../ARCHITECTURE.md).

---

## 2. Prérequis

Outils déjà installés sur le poste (vérifier avec les commandes ci-dessous) :

```bash
docker version     # Docker Desktop DOIT être démarré
k3d version        # K3S dans Docker
kubectl version --client
helm version
faas-cli version   # utile pour la livraison GHCR
```

> Si Docker n'est pas démarré : lancer **Docker Desktop** et attendre qu'il soit prêt.

---

## 3. Déploiement complet (une commande)

À partir de zéro (aucun cluster), tout se déploie automatiquement :

```bash
bash scripts/setup-local.sh
```

Ce script enchaîne :
1. création du cluster k3d (**1 control-plane + 1 worker**) ;
2. correctif du kubeconfig (spécifique Docker Desktop Windows) ;
3. déploiement d'**OpenFaaS** via Helm ;
4. déploiement de **PostgreSQL** + création des **secrets** (clé Fernet, mot de passe DB) ;
5. **build** des images des 3 fonctions + du frontend, puis **import** dans le cluster ;
6. déploiement des **fonctions** et du **frontend**.

À la fin, le script affiche l'URL du frontend et une commande de test.

⏱️ Compter quelques minutes au premier lancement (téléchargement des images de base).

---

## 4. Lancer l'interface web

Le frontend est **déployé dans le cluster** (pas besoin de lancer Streamlit à la main).
Une fois `setup-local.sh` terminé, ouvrez simplement dans votre navigateur :

```
http://cofrap.localhost:8081
```

> `cofrap.localhost` résout automatiquement vers `127.0.0.1`. Le port `8081` est exposé par le
> LoadBalancer de k3d et routé par Traefik vers le frontend.

**Repli** (si l'Ingress pose problème) — exposer le frontend directement :

```bash
kubectl -n openfaas-fn port-forward svc/frontend 8501:8501
# puis ouvrir http://127.0.0.1:8501
```

**Variante hors cluster** (exécuter le frontend depuis le PC, utile en développement) :

```bash
kubectl -n openfaas port-forward svc/gateway 8080:8080          # 1er terminal
OPENFAAS_URL=http://127.0.0.1:8080 ./.venv/Scripts/python.exe -m streamlit run frontend/app.py   # 2e terminal
```

---

## 5. Parcours utilisateur (la démo)

L'interface comporte deux onglets. Le parcours principal est **« Se connecter / S'inscrire »**.

### a) Créer un compte (utilisateur inexistant)
1. Onglet **« Se connecter / S'inscrire »**.
2. Saisir un **nom d'utilisateur** qui n'existe pas (ex. `alexis.demo`), laisser mot de passe/2FA vides.
3. Cliquer **« Se connecter »**.
4. → Le système détecte que le compte n'existe pas et le **crée automatiquement** :
   - affichage du **QR code du mot de passe** (24 caractères, à usage unique) ;
   - affichage du **QR code de la 2FA** (`otpauth://`).
5. **Scanner le QR du mot de passe** (le décoder) pour lire le mot de passe généré.
6. **Scanner le QR 2FA** avec une application d'authentification : *Google Authenticator*,
   *Microsoft Authenticator* ou *FreeOTP*.

### b) S'authentifier
1. Toujours dans l'onglet **« Se connecter / S'inscrire »**.
2. Saisir : **nom d'utilisateur**, **mot de passe** (celui du QR), **code 2FA** (6 chiffres affichés par l'app).
3. Cliquer **« Se connecter »** → **✅ Authentification réussie**.

### c) Cas d'erreur (à montrer au jury)
- **Mauvais code 2FA** ou **mauvais mot de passe** → message d'échec (`401`).

### d) Cas « compte expiré » (rotation 6 mois)
Le sujet impose une rotation tous les 6 mois. Pour le démontrer, on vieillit artificiellement un compte
en base, puis on tente de se connecter :

```bash
# Exposer la gateway si ce n'est pas déjà fait
kubectl -n openfaas-fn port-forward svc/postgres 5432:5432   # (optionnel)

# Vieillir le compte de 7 mois directement en base :
kubectl -n openfaas-fn exec postgres-0 -- \
  psql -U cofrap -d cofrap -c \
  "UPDATE users SET gendate = gendate - 7*30*24*3600 WHERE username='alexis.demo';"
```

Ensuite, dans l'interface, se reconnecter avec `alexis.demo` :
→ le système répond **« identifiants expirés »** et **régénère automatiquement** un nouveau mot de passe
et une nouvelle 2FA (nouveaux QR codes). En base, la colonne `expired` passe à `1`.

> 📸 **Pensez à faire des captures d'écran de chaque étape** (création, QR mot de passe, QR 2FA,
> authentification réussie, message d'expiration) : ce sont des livrables du dossier final.

---

## 6. Publier les images sur GHCR (Mission 6)

Le sujet demande de **téléverser les images sur un dépôt OCI**. Les images sont déjà construites ;
il reste à les pousser sur GitHub Container Registry (`ghcr.io/leo-pro-projects`).

### a) Créer un token GitHub
1. Aller sur **https://github.com/settings/tokens** → **Tokens (classic)**.
2. **Generate new token (classic)**, nom `MSPR-GHCR`, expiration au choix.
3. Cocher le scope **`write:packages`** → **Generate token** → **copier** le token (`ghp_…`).

### b) Pousser les images
```bash
export GHCR_TOKEN=ghp_votre_token
bash scripts/push-ghcr.sh
```

### c) Rendre les paquets publics
Sur **https://github.com/users/leo-pro-projects/packages**, pour chaque paquet
(`cofrap-generate-password`, `cofrap-generate-2fa`, `cofrap-authenticate`, `cofrap-frontend`) :
*Package settings → Change visibility → Public*.

> Pourquoi public ? OpenFaaS **Community Edition** refuse les images privées au déploiement via
> `faas-cli deploy`. Une fois publiques, la voie « standard » `faas-cli up -f stack.yml`
> (build + push + deploy) devient pleinement utilisable.

---

## 7. Vérifier que tout fonctionne

```bash
# Nœuds du cluster (control-plane + worker)
kubectl get nodes

# Pods OpenFaaS (gateway, etc.)
kubectl -n openfaas get pods

# Pods applicatifs (fonctions + frontend + postgres)
kubectl -n openfaas-fn get pods

# Test direct d'une fonction (nécessite le port-forward gateway)
kubectl -n openfaas port-forward svc/gateway 8080:8080 &
curl -s -X POST http://127.0.0.1:8080/function/generate-password -d '{"username":"michel.ranu"}'
```

Une réponse JSON contenant `qrcode_png_base64` = la fonction marche de bout en bout (génération +
chiffrement + écriture en base + QR).

---

## 8. Tests automatisés

Les 3 fonctions sont couvertes par des tests unitaires (base de données **simulée en mémoire**,
donc exécutables **sans cluster**) :

```bash
./.venv/Scripts/python.exe -m pytest tests/ -v
```

Couverture : génération mot de passe (24 car., 4 classes), QR, chiffrement Fernet, TOTP,
authentification (succès / mauvais mot de passe / mauvais OTP / compte inconnu) et **expiration 6 mois**.

---

## 9. Dépannage

| Symptôme | Cause probable | Solution |
|----------|----------------|----------|
| `docker ... daemon is not running` | Docker Desktop arrêté | Lancer Docker Desktop |
| `kubectl` timeout `host.docker.internal` | kubeconfig k3d non corrigé | `PORT=$(docker port k3d-cofrap-serverlb 6443/tcp \| sed 's/.*://'); kubectl config set-cluster k3d-cofrap --server=https://127.0.0.1:$PORT` |
| `http://cofrap.localhost:8081` ne répond pas | Ingress / Traefik | Repli : `kubectl -n openfaas-fn port-forward svc/frontend 8501:8501` |
| Frontend : « gateway injoignable » | OPENFAAS_URL incorrect | En cluster, doit être `http://gateway.openfaas:8080` (déjà injecté) |
| `faas-cli build` : *unsupported protocol scheme c* | Bug chemin Windows de faas-cli | Utiliser `bash scripts/build-images.sh` (build docker manuel) |
| `the Community Edition ... only allows public images` | OpenFaaS CE bloque les images privées | Déploiement via manifests natifs (déjà en place) **ou** pousser les images en **public** sur GHCR |
| `streamlit: command not found` | Streamlit hors du PATH | Utiliser `./.venv/Scripts/python.exe -m streamlit ...` |

---

## 10. Arrêter / nettoyer

```bash
# Supprimer entièrement le cluster (libère les ressources Docker)
bash scripts/teardown-local.sh

# Tout redéployer ensuite
bash scripts/setup-local.sh
```

> Les secrets locaux (`.fernet-key`, `.db-password`) sont conservés entre deux déploiements pour la
> reproductibilité ; ils sont ignorés par Git.

---

## 11. Déroulé conseillé pour la soutenance

Suggestion de séquence (≈ 5–7 min de démo technique dans les 20 min de présentation) :

1. **Contexte & besoin** (30 s) : COFRAP, comptes compromis → mots de passe forts + 2FA + rotation 6 mois.
2. **Architecture** (1 min) : montrer le schéma ([§1](#1-architecture-en-une-image)) — serverless OpenFaaS,
   Kubernetes local (k3d), PostgreSQL, chiffrement.
3. **Le cluster tourne** (30 s) : `kubectl -n openfaas-fn get pods` → tout est *Running*.
4. **Démo live** (2–3 min) sur `http://cofrap.localhost:8081` :
   - créer `demo.jury` → montrer les 2 QR codes ;
   - scanner la 2FA avec un téléphone ;
   - se connecter → ✅ ;
   - montrer un **échec** (mauvais code) ;
   - montrer l'**expiration** (commande SQL + reconnexion → régénération).
5. **Sécurité** (1 min) : ouvrir la table `users` et montrer que `password` et `mfa` sont **chiffrés** :
   ```bash
   kubectl -n openfaas-fn exec postgres-0 -- psql -U cofrap -d cofrap -c "SELECT id, username, left(password,15)||'...' AS password_chiffre, expired FROM users;"
   ```
6. **Qualité** (30 s) : `pytest tests/ -v` → 9 tests verts.
7. **Industrialisation** (30 s) : évoquer le push GHCR (`scripts/push-ghcr.sh`) et le fait que
   l'implémentation finale sera reprise par les équipes Infra (c'est un **PoC**).

**Points à verbaliser pour le barème technique :** choix de Python (librairies), choix de k3d/K3S
(simplicité, vrai cluster), gestion des **secrets**, **chiffrement** des données sensibles,
fonctionnement **serverless** (scale-to-zero = atout d'OpenFaaS, fonctionnalité *Enterprise*),
et difficultés rencontrées + solutions (bug faas-cli Windows, restriction images CE, kubeconfig k3d).

> Le détail des livrables et leur correspondance au barème : [LIVRABLES.md](../LIVRABLES.md).
> L'état d'avancement : [PROGRESS.md](../PROGRESS.md).
