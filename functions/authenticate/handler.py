"""Fonction OpenFaaS : authenticate.

Authentifie un utilisateur à partir de son login, mot de passe et code TOTP.
Vérifie que les identifiants ont moins de 6 mois ; sinon marque le compte `expired=1`
et demande au frontend de relancer le processus de génération.

Entrée  (JSON) : {"username": ..., "password": ..., "otp": "123456"}
Sortie  (JSON) : {"status": "ok" | "expired" | "invalid", "message": ...}
"""
import json
import os
import time

import psycopg2
import pyotp
from cryptography.fernet import Fernet

SIX_MONTHS_SECONDS = 6 * 30 * 24 * 3600  # ≈ 15 552 000 s


def read_secret(name, env_fallback=None):
    path = "/var/openfaas/secrets/%s" % name
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    if env_fallback and os.environ.get(env_fallback):
        return os.environ[env_fallback].strip()
    raise RuntimeError("Secret introuvable : %s" % name)


def db_connect():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "postgres.openfaas-fn.svc.cluster.local"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "cofrap"),
        user=os.environ.get("DB_USER", "cofrap"),
        password=read_secret("db-password", env_fallback="DB_PASSWORD"),
    )


def handle(event, context):
    try:
        body = event.body
        if isinstance(body, (bytes, bytearray)):
            body = body.decode("utf-8")
        payload = json.loads(body) if body else {}
        username = (payload.get("username") or "").strip()
        password = payload.get("password") or ""
        otp = (payload.get("otp") or "").strip()
        if not username or not password or not otp:
            return {"statusCode": 400,
                    "body": json.dumps({"status": "invalid",
                                        "message": "username, password et otp requis"})}

        fernet = Fernet(read_secret("fernet-key", env_fallback="FERNET_KEY").encode())

        conn = db_connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute(
                    "SELECT password, mfa, gendate, expired FROM users WHERE username = %s",
                    (username,),
                )
                row = cur.fetchone()
                if row is None:
                    return {"statusCode": 404,
                            "body": json.dumps({"status": "invalid",
                                                "message": "compte inconnu"})}

                enc_password, enc_mfa, gendate, expired = row

                # 1) Contrôle d'ancienneté (rotation 6 mois)
                age = int(time.time()) - int(gendate or 0)
                if expired == 1 or age > SIX_MONTHS_SECONDS:
                    cur.execute(
                        "UPDATE users SET expired = 1 WHERE username = %s", (username,)
                    )
                    return {"statusCode": 200,
                            "body": json.dumps({
                                "status": "expired",
                                "message": "Identifiants expirés (>6 mois). "
                                           "Relancez la génération du mot de passe et de la 2FA.",
                            })}

                # 2) Vérification mot de passe
                stored_password = fernet.decrypt(enc_password.encode()).decode()
                if password != stored_password:
                    return {"statusCode": 401,
                            "body": json.dumps({"status": "invalid",
                                                "message": "mot de passe incorrect"})}

                # 3) Vérification TOTP
                secret = fernet.decrypt(enc_mfa.encode()).decode()
                if not pyotp.TOTP(secret).verify(otp, valid_window=1):
                    return {"statusCode": 401,
                            "body": json.dumps({"status": "invalid",
                                                "message": "code 2FA incorrect"})}
        finally:
            conn.close()

        return {"statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"status": "ok",
                                    "message": "Authentification réussie"})}
    except Exception as exc:  # noqa: BLE001
        return {"statusCode": 500, "body": json.dumps({"status": "error", "message": str(exc)})}
