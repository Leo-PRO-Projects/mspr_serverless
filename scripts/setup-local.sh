#!/usr/bin/env bash
# Déploiement complet du PoC COFRAP en local (k3d + OpenFaaS + PostgreSQL + fonctions).
# Idempotent : réutilise les secrets générés (.fernet-key / .db-password) s'ils existent.
#
# Prérequis : docker (démarré), k3d, kubectl, helm, python (venv .venv pour build/tests).
# Usage : bash scripts/setup-local.sh
set -euo pipefail
cd "$(dirname "$0")/.."

CLUSTER=cofrap

gen() { head -c 24 /dev/urandom | base64 | tr -d '+/=' | cut -c1-"$1"; }

# --- Secrets persistés (générés une seule fois) ---------------------------- #
[ -f .fernet-key ]  || .venv/Scripts/python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > .fernet-key
[ -f .db-password ] || echo "cofrap_$(gen 12)" > .db-password
FERNET=$(cat .fernet-key); DBPW=$(cat .db-password)

# --- 1. Cluster k3d -------------------------------------------------------- #
if ! k3d cluster list 2>/dev/null | grep -q "^${CLUSTER} "; then
  echo "== Création du cluster k3d =="
  k3d cluster create --config infra/k3d/cluster.yaml
fi
# Correctif kubeconfig Windows/Docker Desktop : host.docker.internal -> 127.0.0.1
PORT=$(docker port k3d-${CLUSTER}-serverlb 6443/tcp | head -1 | sed 's/.*://')
kubectl config set-cluster k3d-${CLUSTER} --server="https://127.0.0.1:${PORT}" >/dev/null
kubectl wait --for=condition=Ready nodes --all --timeout=120s

# --- 2. OpenFaaS via Helm -------------------------------------------------- #
echo "== OpenFaaS (Helm) =="
kubectl apply -f https://raw.githubusercontent.com/openfaas/faas-netes/master/namespaces.yml
helm repo add openfaas https://openfaas.github.io/faas-netes/ >/dev/null 2>&1 || true
helm repo update >/dev/null
if ! kubectl -n openfaas get secret basic-auth >/dev/null 2>&1; then
  kubectl -n openfaas create secret generic basic-auth \
    --from-literal=basic-auth-user=admin \
    --from-literal=basic-auth-password="$(gen 16)"
fi
helm upgrade openfaas --install openfaas/openfaas -n openfaas -f infra/helm/values-openfaas.yaml

# --- 3. Base de données + secrets ------------------------------------------ #
echo "== PostgreSQL + secrets =="
kubectl -n openfaas-fn create secret generic cofrap-db   --from-literal=db-password="$DBPW"  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n openfaas-fn create secret generic fernet-key  --from-literal=fernet-key="$FERNET" --dry-run=client -o yaml | kubectl apply -f -
kubectl -n openfaas-fn create secret generic db-password --from-literal=db-password="$DBPW"  --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -f infra/database/postgres.yaml

# --- 4. Build + import des images des fonctions ---------------------------- #
echo "== Build des images =="
bash scripts/build-images.sh
k3d image import -c ${CLUSTER} \
  ghcr.io/leo-pro-projects/cofrap-generate-password:0.1.0 \
  ghcr.io/leo-pro-projects/cofrap-generate-2fa:0.1.0 \
  ghcr.io/leo-pro-projects/cofrap-authenticate:0.1.0 \
  ghcr.io/leo-pro-projects/cofrap-frontend:0.1.0

# --- 5. Déploiement des fonctions (manifests natifs) ----------------------- #
echo "== Déploiement des fonctions =="
kubectl -n openfaas rollout status deploy/gateway --timeout=180s
kubectl -n openfaas-fn rollout status statefulset/postgres --timeout=180s
kubectl apply -f infra/k8s/functions.yaml
kubectl apply -f infra/k8s/frontend.yaml
kubectl -n openfaas-fn rollout status deploy/generate-password --timeout=120s
kubectl -n openfaas-fn rollout status deploy/generate-2fa --timeout=120s
kubectl -n openfaas-fn rollout status deploy/authenticate --timeout=120s
kubectl -n openfaas-fn rollout status deploy/frontend --timeout=120s

cat <<EOF

✅ PoC déployé (fonctions + frontend dans le cluster).

Frontend (servi par le cluster via Traefik) :
   http://cofrap.localhost:8081

Gateway OpenFaaS (pour tests directs) :
   kubectl -n openfaas port-forward svc/gateway 8080:8080
   curl -s -X POST http://127.0.0.1:8080/function/generate-password -d '{"username":"michel.ranu"}'
EOF
