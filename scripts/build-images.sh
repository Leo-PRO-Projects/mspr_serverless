#!/usr/bin/env bash
# Construit les images des 3 fonctions OpenFaaS sans faas-cli build
# (contournement du bug de chemin Windows de faas-cli). Reproduit l'assemblage
# du template python3-http-debian : template + function/<code>.
set -euo pipefail

TEMPLATE="template/python3-http-debian"
REGISTRY="ghcr.io/leo-pro-projects"
TAG="0.1.0"
FUNCS=(generate-password generate-2fa authenticate)

# Récupère le template OpenFaaS s'il est absent (non versionné : code tiers).
[ -d "$TEMPLATE" ] || faas-cli template store pull python3-http-debian

for fn in "${FUNCS[@]}"; do
  ctx="build/${fn}"
  echo "=== Build ${fn} ==="
  rm -rf "$ctx"
  mkdir -p "$ctx/function"
  cp -r "$TEMPLATE"/. "$ctx"/
  cp "functions/${fn}/handler.py"       "$ctx/function/handler.py"
  cp "functions/${fn}/requirements.txt" "$ctx/function/requirements.txt"
  : > "$ctx/function/__init__.py"
  docker build -t "${REGISTRY}/cofrap-${fn}:${TAG}" "$ctx"
done

# --- Frontend (image Streamlit, build docker classique) -------------------- #
echo "=== Build frontend ==="
docker build -t "${REGISTRY}/cofrap-frontend:${TAG}" frontend

echo "=== Images construites ==="
docker images | grep cofrap- || true
