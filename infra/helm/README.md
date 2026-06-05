# Déploiement de l'infrastructure — K3S (VMs) + OpenFaaS + PostgreSQL

> ℹ️ **Voie retenue pour ce projet : déploiement 100 % local avec k3d** → voir
> [`infra/k3d/README.md`](../k3d/README.md) et `scripts/setup-local.sh`.
> Le présent document décrit la variante **K3S sur VMs** (alternative « bare‑metal », conforme au sujet),
> conservée à titre de documentation pour une implémentation type production.

Procédure de mise en place du PoC sur un cluster **K3S** (1 control-plane + 1 worker).

## 0. Prérequis (postes de travail)

```bash
# kubectl, helm, faas-cli
curl -sLS https://dl.get-arkade.dev | sudo sh      # (optionnel) arkade simplifie l'install
curl -sSLf https://cli.openfaas.com | sudo sh      # faas-cli
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

## 1. Provisionner le cluster K3S

```bash
# Sur la VM control-plane (2 vCPU / 2-4 Go) :
curl -sfL https://get.k3s.io | sh -
sudo cat /var/lib/rancher/k3s/server/node-token        # récupérer le token

# Sur la VM worker (2 vCPU / 4 Go) :
curl -sfL https://get.k3s.io | K3S_URL=https://<IP-control-plane>:6443 K3S_TOKEN=<token> sh -

# Récupérer le kubeconfig (control-plane) : /etc/rancher/k3s/k3s.yaml
# Remplacer 127.0.0.1 par l'IP du control-plane, puis exporter :
export KUBECONFIG=~/.kube/k3s.yaml
kubectl get nodes        # doit lister control-plane + worker
```

> K3S inclut déjà un LoadBalancer (svclb) et l'Ingress Traefik → pas besoin de MetalLB/Ingress-nginx.

## 2. Déployer OpenFaaS via Helm (chart faas-netes)

```bash
kubectl apply -f https://raw.githubusercontent.com/openfaas/faas-netes/master/namespaces.yml
helm repo add openfaas https://openfaas.github.io/faas-netes/
helm repo update

# Mot de passe gateway
PASSWORD=$(head -c 12 /dev/urandom | base64 | tr -d '+/=')
kubectl -n openfaas create secret generic basic-auth \
  --from-literal=basic-auth-user=admin \
  --from-literal=basic-auth-password="$PASSWORD"

helm upgrade openfaas --install openfaas/openfaas \
  --namespace openfaas \
  -f ../helm/values-openfaas.yaml

kubectl apply -f ../k8s/ingress.yaml
```

## 3. Connexion faas-cli

```bash
export OPENFAAS_URL=http://openfaas.local      # ou l'URL de l'Ingress / nip.io
echo -n $PASSWORD | faas-cli login --username admin --password-stdin
```

## 4. Base de données PostgreSQL

```bash
# Secret du mot de passe DB (sert au StatefulSet ET aux fonctions)
kubectl -n openfaas-fn create secret generic cofrap-db \
  --from-literal=db-password='<motdepasse>'

kubectl apply -f ../database/postgres.yaml
kubectl -n openfaas-fn rollout status statefulset/postgres
```

## 5. Secrets des fonctions (OpenFaaS secrets)

```bash
# Clé de chiffrement Fernet
FERNET=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
faas-cli secret create fernet-key   --from-literal="$FERNET"
faas-cli secret create db-password  --from-literal='<motdepasse>'
```

## 6. Déployer les fonctions + le frontend

```bash
cd ../..                       # racine du dépôt
faas-cli up -f stack.yml       # build + push (GHCR) + deploy des 3 fonctions
```

## Vérifications utiles

```bash
kubectl -n openfaas get pods
kubectl -n openfaas-fn get pods
faas-cli list
```
