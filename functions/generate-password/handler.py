"""Fonction OpenFaaS : generate-password.

Génère un mot de passe robuste (24 caractères, 4 classes) pour un utilisateur,
le chiffre (Fernet) et le stocke en base, puis renvoie un QR Code (PNG base64)
contenant le mot de passe en clair (transmission unique à l'utilisateur).

Entrée  (JSON) : {"username": "michel.ranu"}
Sortie  (JSON) : {"username": ..., "qrcode_png_base64": ..., "gendate": ...}
"""
import base64
import io
import json
import os
import secrets
import string
import time

import psycopg2
import qrcode
from cryptography.fernet import Fernet

PASSWORD_LENGTH = 24


def read_secret(name, env_fallback=None):
    """Lit un secret OpenFaaS monté, avec repli sur variable d'environnement."""
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


def generate_password(length=PASSWORD_LENGTH):
    """Mot de passe garantissant >=1 majuscule, minuscule, chiffre, caractère spécial."""
    specials = "!@#$%^&*()-_=+[]{};:,.<>?"
    pools = [string.ascii_uppercase, string.ascii_lowercase, string.digits, specials]
    chars = "".join(pools)
    while True:
        pwd = "".join(secrets.choice(chars) for _ in range(length))
        if (any(c in string.ascii_uppercase for c in pwd)
                and any(c in string.ascii_lowercase for c in pwd)
                and any(c in string.digits for c in pwd)
                and any(c in specials for c in pwd)):
            return pwd


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
        password = generate_password()
        encrypted = fernet.encrypt(password.encode()).decode()
        gendate = int(time.time())

        conn = db_connect()
        try:
            with conn, conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (username, password, gendate, expired)
                    VALUES (%s, %s, %s, 0)
                    ON CONFLICT (username)
                    DO UPDATE SET password = EXCLUDED.password,
                                  gendate  = EXCLUDED.gendate,
                                  expired  = 0
                    """,
                    (username, encrypted, gendate),
                )
        finally:
            conn.close()

        qr = make_qrcode_png_base64(password)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "username": username,
                "qrcode_png_base64": qr,
                "gendate": gendate,
            }),
        }
    except Exception as exc:  # noqa: BLE001 — renvoyer une erreur exploitable au frontend
        return {"statusCode": 500, "body": json.dumps({"error": str(exc)})}
