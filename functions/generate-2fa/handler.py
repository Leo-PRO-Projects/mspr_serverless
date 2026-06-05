"""Fonction OpenFaaS : generate-2fa.

Génère un secret TOTP pour un utilisateur, le chiffre (Fernet) et le stocke en base,
puis renvoie un QR Code (PNG base64) au format `otpauth://` scannable par une
application d'authentification (Google/Microsoft Authenticator, FreeOTP...).

Entrée  (JSON) : {"username": "michel.ranu"}
Sortie  (JSON) : {"username": ..., "qrcode_png_base64": ..., "otpauth_uri": ...}
"""
import base64
import io
import json
import os
import time

import psycopg2
import pyotp
import qrcode
from cryptography.fernet import Fernet

ISSUER = "COFRAP"


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


def make_qrcode_png_base64(data):
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def handle(event, context):
    try:
        body = event.body
        if isinstance(body, (bytes, bytearray)):
            body = body.decode("utf-8")
        payload = json.loads(body) if body else {}
        username = (payload.get("username") or "").strip()
        if not username:
            return {"statusCode": 400, "body": json.dumps({"error": "username requis"})}

        fernet = Fernet(read_secret("fernet-key", env_fallback="FERNET_KEY").encode())
        secret = pyotp.random_base32()
        encrypted = fernet.encrypt(secret.encode()).decode()
        gendate = int(time.time())

        otpauth_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=username, issuer_name=ISSUER
        )

        conn = db_connect()
        try:
            with conn, conn.cursor() as cur:
                # L'utilisateur doit exister (créé par generate-password) ; on met à jour le 2FA.
                cur.execute(
                    """
                    INSERT INTO users (username, mfa, gendate, expired)
                    VALUES (%s, %s, %s, 0)
                    ON CONFLICT (username)
                    DO UPDATE SET mfa     = EXCLUDED.mfa,
                                  gendate = EXCLUDED.gendate,
                                  expired = 0
                    """,
                    (username, encrypted, gendate),
                )
        finally:
            conn.close()

        qr = make_qrcode_png_base64(otpauth_uri)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "username": username,
                "qrcode_png_base64": qr,
                "otpauth_uri": otpauth_uri,
            }),
        }
    except Exception as exc:  # noqa: BLE001
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}
