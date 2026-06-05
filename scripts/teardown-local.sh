#!/usr/bin/env bash
# Supprime le cluster k3d du PoC (les secrets locaux .fernet-key/.db-password sont conservés).
# Usage : bash scripts/teardown-local.sh
set -euo pipefail
k3d cluster delete cofrap
echo "Cluster 'cofrap' supprimé. (Relancer : bash scripts/setup-local.sh)"
