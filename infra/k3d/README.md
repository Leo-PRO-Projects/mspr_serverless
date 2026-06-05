# Déploiement local — k3d (K3S dans Docker)

Architecture **100 % locale** : un vrai cluster K3S tourne dans des conteneurs Docker sur le PC,
sans aucune VM. Reproduit l'architecture du sujet (control-plane + worker, Traefik, LoadBalancer).

## Prérequis (déjà installés sur le poste de dev)

| Outil | Rôle |
|-------|------|
| Docker Desktop | exécute les nœuds k3d + builds d'images |
| k3d | crée le cluster K3S dans Docker |
| kubectl | pilote le cluster |
| helm | déploie OpenFaaS |
| python + `.venv` | build/test des fonctions |
| faas-cli | *(optionnel)* voie de livraison standard via GHCR |

## Déploiement automatique (recommandé)

```bash
bash scripts/setup-local.sh          # tout : cluster + OpenFaaS + PostgreSQL + fonctions
kubectl -n openfaas port-forward svc/gateway 8080:8080   # expose la gateway
```

`teardown-local.sh` supprime le cluster.

## Déploiement manuel (pas à pas)

```bash
# 1) Cluster (1 control-plane + 1 worker)
k3d cluster create --config infra/k3d/cluster.yaml

# 2) Correctif kubeconfig (Docker Desktop Windows) : host.docker.internal -> 127.0.0.1
PORT=$(docker port k3d-cofrap-serverlb 6443/tcp | head -1 | sed 's/.*://')
kubectl config set-cluster k3d-cofrap --server="https://127.0.0.1:${PORT}"

# 3) OpenFaaS
kubectl apply -f https://raw.githubusercontent.com/openfaas/faas-netes/master/namespaces.yml
helm repo add openfaas https://openfaas.github.io/faas-netes/ && helm repo update
kubectl -n openfaas create secret generic basic-auth \
  --from-literal=basic-auth-user=admin --from-literal=basic-auth-password=admin
helm upgrade openfaas --install openfaas/openfaas -n openfaas -f infra/helm/values-openfaas.yaml

# 4) Secrets + base de données
kubectl -n openfaas-fn create secret generic cofrap-db   --from-literal=db-password=<mdp>
kubectl -n openfaas-fn create secret generic db-password --from-literal=db-password=<mdp>
kubectl -n openfaas-fn create secret generic fernet-key  --from-literal=fernet-key=<clé Fernet>
kubectl apply -f infra/database/postgres.yaml

# 5) Build + import des images (contourne le bug de chemin Windows de faas-cli build)
bash scripts/build-images.sh
k3d image import -c cofrap \
  ghcr.io/leo-pro-projects/cofrap-generate-password:0.1.0 \
  ghcr.io/leo-pro-projects/cofrap-generate-2fa:0.1.0 \
  ghcr.io/leo-pro-projects/cofrap-authenticate:0.1.0

# 6) Déploiement des fonctions
kubectl apply -f infra/k8s/functions.yaml
```

## Pourquoi des manifests natifs pour les fonctions ?

OpenFaaS **Community Edition** refuse les images non publiques via son API de déploiement
(`faas-cli deploy` → *"the Community Edition license agreement only allows public images"*).
Pour rester strictement local (images importées dans k3d, **aucun registre externe**), on déploie
les fonctions en **Deployments + Services Kubernetes** portant le label `faas_function` : la gateway
OpenFaaS les reconnaît et route `/function/<nom>` vers elles. Voir `infra/k8s/functions.yaml`.

## Voie de livraison « standard » (GHCR)

Pour la conformité au sujet (*« uploader les images sur un dépôt OCI »*), la voie officielle est :

```bash
echo $GHCR_TOKEN | docker login ghcr.io -u leo-pro-projects --password-stdin
faas-cli up -f stack.yml      # build + push GHCR + deploy
```
(nécessite un *Personal Access Token* GitHub avec `write:packages` et les paquets rendus **publics**).

## Tests

```bash
# Invocation directe
curl -s -X POST http://127.0.0.1:8080/function/generate-password -d '{"username":"michel.ranu"}'

# Suite unitaire (DB simulée, sans cluster)
.venv/Scripts/python -m pytest tests/ -v
```
