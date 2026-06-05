# Frontend de démonstration

Application **Streamlit** simple pour démontrer le cycle complet : création de compte
(QR mot de passe + QR 2FA), authentification, et relance si compte expiré.

## Lancement local

```bash
pip install -r requirements.txt
export OPENFAAS_URL=http://openfaas.local      # URL de la gateway OpenFaaS
streamlit run app.py
```

## Écrans
- **Créer un compte** : appelle `generate-password` puis `generate-2fa`, affiche les 2 QR codes.
- **Se connecter** : appelle `authenticate` (login + mot de passe + code TOTP) ; gère le cas `expired`.

> Pour la soutenance : scanner le QR mot de passe pour le lire, le QR 2FA avec une app
> d'authentification (Google/Microsoft Authenticator, FreeOTP), puis se connecter.
