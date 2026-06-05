#!/usr/bin/env bash
# Pousse les 4 images sur GHCR (dépôt OCI) — Mission 6 du sujet.
# Prérequis : un Personal Access Token GitHub avec le scope `write:packages`.
#
# Usage :
#   export GHCR_TOKEN=ghp_xxx
#   bash scripts/push-ghcr.sh
#
# Après le 1er push, rendre les paquets PUBLICS sur github.com/users/leo-pro-projects/packages
# (sinon OpenFaaS Community refusera les images au déploiement via faas-cli).
set -euo pipefail

USER="leo-pro-projects"
REGISTRY="ghcr.io/${USER}"
TAG="0.1.0"
IMAGES=(cofrap-generate-password cofrap-generate-2fa cofrap-authenticate cofrap-frontend)

: "${GHCR_TOKEN:?Définir GHCR_TOKEN (PAT GitHub avec write:packages)}"
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$USER" --password-stdin

for img in "${IMAGES[@]}"; do
  echo "== Push ${REGISTRY}/${img}:${TAG} =="
  docker push "${REGISTRY}/${img}:${TAG}"
done

echo "✅ Images poussées sur GHCR. Pensez à les rendre publiques."
