"""Frontend de démonstration COFRAP (Streamlit).

Objectif strictement limité à la démo : création de compte (mot de passe + 2FA via QR),
authentification, et relance du cycle en cas de compte expiré.

Lancement :
    export OPENFAAS_URL=http://openfaas.local
    streamlit run app.py
"""
import base64
import os

import requests
import streamlit as st

GATEWAY = os.environ.get("OPENFAAS_URL", "http://openfaas.local").rstrip("/")


def call_function(name, payload):
    url = "%s/function/%s" % (GATEWAY, name)
    resp = requests.post(url, json=payload, timeout=30)
    try:
        return resp.status_code, resp.json()
    except ValueError:
        return resp.status_code, {"raw": resp.text}


def show_qr(b64_png, caption):
    st.image(base64.b64decode(b64_png), caption=caption, width=240)


st.set_page_config(page_title="COFRAP — Démo Serverless", page_icon="🔐")
st.title("🔐 COFRAP — Gestion de comptes Serverless")
st.caption("Démo OpenFaaS — Gateway : %s" % GATEWAY)

tab_create, tab_login = st.tabs(["Créer un compte", "Se connecter"])

with tab_create:
    st.subheader("Création de compte")
    username = st.text_input("Nom d'utilisateur", key="create_user")
    if st.button("Générer mot de passe + 2FA", key="btn_create"):
        if not username:
            st.warning("Saisissez un nom d'utilisateur.")
        else:
            code, pwd = call_function("generate-password", {"username": username})
            if code == 200 and pwd.get("qrcode_png_base64"):
                st.success("Mot de passe généré. Scannez le QR (usage unique).")
                show_qr(pwd["qrcode_png_base64"], "Mot de passe (QR Code)")
                code2, mfa = call_function("generate-2fa", {"username": username})
                if code2 == 200 and mfa.get("qrcode_png_base64"):
                    st.success("2FA générée. Scannez avec votre application d'authentification.")
                    show_qr(mfa["qrcode_png_base64"], "2FA / TOTP (QR Code)")
                else:
                    st.error("Échec génération 2FA : %s" % mfa)
            else:
                st.error("Échec génération mot de passe : %s" % pwd)

with tab_login:
    st.subheader("Authentification")
    luser = st.text_input("Nom d'utilisateur", key="login_user")
    lpass = st.text_input("Mot de passe", type="password", key="login_pass")
    lotp = st.text_input("Code 2FA (6 chiffres)", key="login_otp")
    if st.button("Se connecter", key="btn_login"):
        code, res = call_function(
            "authenticate", {"username": luser, "password": lpass, "otp": lotp}
        )
        status = res.get("status")
        if status == "ok":
            st.success("✅ " + res.get("message", "Authentification réussie"))
        elif status == "expired":
            st.warning("⏳ " + res.get("message", "Compte expiré — relancez la création."))
        else:
            st.error("❌ " + res.get("message", "Échec de l'authentification"))
