"""Frontend de démonstration COFRAP (Streamlit).

Flux conforme à l'expression du besoin du sujet :
- authentifier un utilisateur (login + mot de passe + code 2FA) ;
- le **créer s'il n'existe pas** (génération mot de passe + 2FA, transmis par QR codes) ;
- **relancer** la génération du mot de passe et de la 2FA si le compte est **expiré** (> 6 mois).

Lancement local :
    OPENFAAS_URL=http://127.0.0.1:8080 streamlit run app.py
En cluster : la variable OPENFAAS_URL pointe vers http://gateway.openfaas:8080 (injectée par le Deployment).
"""
import base64
import os

import requests
import streamlit as st

GATEWAY = os.environ.get("OPENFAAS_URL", "http://127.0.0.1:8080").rstrip("/")


def call_function(name, payload):
    """Invoque une fonction OpenFaaS via la gateway ; renvoie (status_code, dict)."""
    try:
        resp = requests.post("%s/function/%s" % (GATEWAY, name), json=payload, timeout=30)
    except requests.RequestException as exc:
        return 0, {"error": "gateway injoignable : %s" % exc}
    try:
        return resp.status_code, resp.json()
    except ValueError:
        return resp.status_code, {"raw": resp.text}


def show_qr(b64_png, caption):
    st.image(base64.b64decode(b64_png), caption=caption, width=240)


def generer_identifiants(username):
    """Génère (ou régénère) mot de passe + 2FA pour `username` et affiche les 2 QR codes.

    Réutilisé pour la création initiale ET pour la relance d'un compte expiré.
    """
    code, pwd = call_function("generate-password", {"username": username})
    if code != 200 or not pwd.get("qrcode_png_base64"):
        st.error("Échec de la génération du mot de passe : %s" % pwd)
        return False
    st.success("Mot de passe généré. Scannez ce QR code (transmission à usage unique).")
    show_qr(pwd["qrcode_png_base64"], "Mot de passe (QR Code)")

    code2, mfa = call_function("generate-2fa", {"username": username})
    if code2 != 200 or not mfa.get("qrcode_png_base64"):
        st.error("Échec de la génération de la 2FA : %s" % mfa)
        return False
    st.success("2FA générée. Scannez ce QR code avec votre application d'authentification.")
    show_qr(mfa["qrcode_png_base64"], "2FA / TOTP (QR Code)")
    st.info("Votre compte est prêt. Reconnectez-vous avec votre mot de passe et un code 2FA.")
    return True


st.set_page_config(page_title="COFRAP — Démo Serverless", page_icon="🔐")
st.title("🔐 COFRAP — Gestion de comptes Serverless")
st.caption("Démo OpenFaaS — Gateway : %s" % GATEWAY)

tab_login, tab_create = st.tabs(["Se connecter / S'inscrire", "Créer un compte"])

# --------------------------------------------------------------------------- #
# Onglet principal : authentification avec création/relance automatiques       #
# --------------------------------------------------------------------------- #
with tab_login:
    st.subheader("Authentification")
    st.write("Saisissez vos identifiants. Si le compte n'existe pas, il sera créé. "
             "S'il est expiré (> 6 mois), de nouveaux identifiants seront générés.")
    luser = st.text_input("Nom d'utilisateur", key="login_user")
    lpass = st.text_input("Mot de passe", type="password", key="login_pass")
    lotp = st.text_input("Code 2FA (6 chiffres)", key="login_otp")

    if st.button("Se connecter", key="btn_login"):
        if not luser:
            st.warning("Saisissez au moins un nom d'utilisateur.")
        else:
            code, res = call_function(
                "authenticate", {"username": luser, "password": lpass, "otp": lotp}
            )
            status = res.get("status")

            if status == "ok":
                st.success("✅ " + res.get("message", "Authentification réussie"))

            elif status == "expired":
                # Exigence du sujet : relancer la création de mot de passe + 2FA.
                st.warning("⏳ Identifiants expirés (> 6 mois). Régénération en cours…")
                generer_identifiants(luser)

            elif code == 404:
                # Exigence du sujet : créer le compte s'il n'existe pas.
                st.info("🆕 Compte inexistant — création en cours…")
                generer_identifiants(luser)

            else:
                st.error("❌ " + res.get("message", "Échec de l'authentification"))

# --------------------------------------------------------------------------- #
# Onglet secondaire : création explicite d'un compte                           #
# --------------------------------------------------------------------------- #
with tab_create:
    st.subheader("Création de compte")
    st.write("Génère directement un mot de passe et une 2FA pour un nouvel utilisateur.")
    cuser = st.text_input("Nom d'utilisateur", key="create_user")
    if st.button("Générer mot de passe + 2FA", key="btn_create"):
        if not cuser:
            st.warning("Saisissez un nom d'utilisateur.")
        else:
            generer_identifiants(cuser)
