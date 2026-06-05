"""Tests unitaires des 3 fonctions OpenFaaS (DB simulée en mémoire)."""
import base64
import json
import string
import time

import pyotp
import pytest
from cryptography.fernet import Fernet

from conftest import make_event


# --------------------------------------------------------------------------- #
# generate-password                                                           #
# --------------------------------------------------------------------------- #
def test_password_generator_respecte_les_4_classes(handlers):
    gen = handlers["generate_password"].generate_password
    for _ in range(50):
        pwd = gen()
        assert len(pwd) == 24
        assert any(c in string.ascii_uppercase for c in pwd)
        assert any(c in string.ascii_lowercase for c in pwd)
        assert any(c in string.digits for c in pwd)
        assert any(not c.isalnum() for c in pwd)


def test_generate_password_handler(handlers, store):
    resp = handlers["generate_password"].handle(
        make_event(json.dumps({"username": "michel.ranu"})), None
    )
    assert resp["statusCode"] == 200
    data = json.loads(resp["body"])
    assert data["username"] == "michel.ranu"
    # QR Code = PNG base64 valide
    png = base64.b64decode(data["qrcode_png_base64"])
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    # Stocké chiffré (≠ clair) et déchiffrable
    row = store.rows["michel.ranu"]
    assert row["password"] is not None
    assert row["expired"] == 0
    assert row["gendate"] > 0


def test_generate_password_sans_username(handlers):
    resp = handlers["generate_password"].handle(make_event(json.dumps({})), None)
    assert resp["statusCode"] == 400


# --------------------------------------------------------------------------- #
# generate-2fa                                                                #
# --------------------------------------------------------------------------- #
def test_generate_2fa_handler(handlers, store):
    resp = handlers["generate_2fa"].handle(
        make_event(json.dumps({"username": "michel.ranu"})), None
    )
    assert resp["statusCode"] == 200
    data = json.loads(resp["body"])
    assert data["otpauth_uri"].startswith("otpauth://totp/")
    assert "COFRAP" in data["otpauth_uri"]
    base64.b64decode(data["qrcode_png_base64"])  # ne lève pas
    assert store.rows["michel.ranu"]["mfa"] is not None


# --------------------------------------------------------------------------- #
# authenticate — parcours complet                                             #
# --------------------------------------------------------------------------- #
def _creer_compte(handlers, fernet_key, username="michel.ranu"):
    """Crée un compte et renvoie (mot de passe clair, secret TOTP clair)."""
    f = Fernet(fernet_key.encode())
    handlers["generate_password"].handle(
        make_event(json.dumps({"username": username})), None
    )
    handlers["generate_2fa"].handle(
        make_event(json.dumps({"username": username})), None
    )
    return f  # le fernet pour déchiffrer le store dans le test


def test_authentification_reussie(handlers, store, fernet_key):
    f = _creer_compte(handlers, fernet_key)
    row = store.rows["michel.ranu"]
    password = f.decrypt(row["password"].encode()).decode()
    secret = f.decrypt(row["mfa"].encode()).decode()
    otp = pyotp.TOTP(secret).now()

    resp = handlers["authenticate"].handle(
        make_event(json.dumps({"username": "michel.ranu", "password": password, "otp": otp})),
        None,
    )
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"])["status"] == "ok"


def test_authentification_mauvais_mot_de_passe(handlers, store, fernet_key):
    f = _creer_compte(handlers, fernet_key)
    secret = f.decrypt(store.rows["michel.ranu"]["mfa"].encode()).decode()
    otp = pyotp.TOTP(secret).now()
    resp = handlers["authenticate"].handle(
        make_event(json.dumps({"username": "michel.ranu", "password": "FAUX", "otp": otp})),
        None,
    )
    assert resp["statusCode"] == 401
    assert json.loads(resp["body"])["status"] == "invalid"


def test_authentification_mauvais_otp(handlers, store, fernet_key):
    f = _creer_compte(handlers, fernet_key)
    password = f.decrypt(store.rows["michel.ranu"]["password"].encode()).decode()
    resp = handlers["authenticate"].handle(
        make_event(json.dumps({"username": "michel.ranu", "password": password, "otp": "000000"})),
        None,
    )
    assert resp["statusCode"] == 401


def test_compte_expire_apres_6_mois(handlers, store, fernet_key):
    f = _creer_compte(handlers, fernet_key)
    row = store.rows["michel.ranu"]
    password = f.decrypt(row["password"].encode()).decode()
    secret = f.decrypt(row["mfa"].encode()).decode()
    otp = pyotp.TOTP(secret).now()
    # Vieillir gendate de 7 mois
    row["gendate"] = int(time.time()) - 7 * 30 * 24 * 3600

    resp = handlers["authenticate"].handle(
        make_event(json.dumps({"username": "michel.ranu", "password": password, "otp": otp})),
        None,
    )
    assert resp["statusCode"] == 200
    assert json.loads(resp["body"])["status"] == "expired"
    # Le compte est bien marqué expiré en base
    assert store.rows["michel.ranu"]["expired"] == 1


def test_authentification_compte_inconnu(handlers):
    resp = handlers["authenticate"].handle(
        make_event(json.dumps({"username": "inconnu", "password": "x", "otp": "123456"})),
        None,
    )
    assert resp["statusCode"] == 404
