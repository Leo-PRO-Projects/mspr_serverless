# Frontend de démonstration

Application **Streamlit** simple démontrant le cycle complet conforme au sujet :
- **authentification** (login + mot de passe + code 2FA) ;
- **création du compte s'il n'existe pas** (génération mot de passe + 2FA via QR codes) ;
- **relance automatique** de la génération si le compte est **expiré** (> 6 mois).

## Accès — frontend déployé dans le cluster (recommandé)

Déployé par `scripts/setup-local.sh` (Deployment + Service + Ingress Traefik) :

```
http://cofrap.localhost:8081
```

Le pod appelle la gateway OpenFaaS par son DNS interne (`http://gateway.openfaas:8080`).

> Repli si besoin : `kubectl -n openfaas-fn port-forward svc/frontend 8501:8501` → http://127.0.0.1:8501

## Accès — exécution locale (hors cluster)

```bash
# Gateway exposée localement dans un autre terminal :
kubectl -n openfaas port-forward svc/gateway 8080:8080

# Puis (Git Bash) :
OPENFAAS_URL=http://127.0.0.1:8080 ../.venv/Scripts/python.exe -m streamlit run app.py
```

## Scénario de démonstration
1. Onglet **« Se connecter / S'inscrire »** : saisir un nom inexistant → le compte est **créé** (2 QR codes).
2. Scanner le **QR 2FA** avec une app d'authentification (Google/Microsoft Authenticator, FreeOTP).
3. Se reconnecter avec login + mot de passe + code 2FA → **✅ Authentification réussie**.
4. Cas **expiré** : un compte de plus de 6 mois déclenche la **régénération** automatique des identifiants.

> Pensez aux **captures d'écran** de chaque étape (livrable du dossier final).
