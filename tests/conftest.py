"""Outillage de test : chargement des handlers + PostgreSQL simulé en mémoire.

Les handlers des 3 fonctions portent tous le même nom de module (`handler`).
On les charge depuis leur chemin de fichier sous des noms distincts.
La connexion DB est remplacée par un faux store partagé en mémoire.
"""
import importlib.util
import os
import types
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# PostgreSQL simulé                                                            #
# --------------------------------------------------------------------------- #
class FakeStore:
    """Une table `users` en mémoire : {username: {password, mfa, gendate, expired}}."""

    def __init__(self):
        self.rows = {}


class FakeCursor:
    def __init__(self, store):
        self.store = store
        self._result = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        params = params or ()
        s = " ".join(sql.lower().split())

        if s.startswith("insert into users") and "password" in s:
            username, password, gendate = params
            row = self.store.rows.get(username, {})
            row.update({"password": password, "gendate": gendate, "expired": 0})
            row.setdefault("mfa", None)
            self.store.rows[username] = row

        elif s.startswith("insert into users") and "mfa" in s:
            username, mfa, gendate = params
            row = self.store.rows.get(username, {})
            row.update({"mfa": mfa, "gendate": gendate, "expired": 0})
            row.setdefault("password", None)
            self.store.rows[username] = row

        elif s.startswith("select password, mfa, gendate, expired"):
            username = params[0]
            row = self.store.rows.get(username)
            if row is None:
                self._result = None
            else:
                self._result = (row["password"], row["mfa"], row["gendate"], row["expired"])

        elif s.startswith("update users set expired = 1"):
            username = params[0]
            if username in self.store.rows:
                self.store.rows[username]["expired"] = 1

        else:
            raise AssertionError("SQL non géré par le mock : %s" % sql)

    def fetchone(self):
        return self._result


class FakeConn:
    def __init__(self, store):
        self.store = store

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def cursor(self):
        return FakeCursor(self.store)

    def close(self):
        pass


# --------------------------------------------------------------------------- #
# Chargement des handlers                                                      #
# --------------------------------------------------------------------------- #
def _load(module_name, relpath):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def fernet_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("FERNET_KEY", key)
    monkeypatch.setenv("DB_PASSWORD", "test")
    return key


@pytest.fixture()
def store():
    return FakeStore()


@pytest.fixture()
def handlers(store, fernet_key):
    """Charge les 3 handlers en branchant leur db_connect sur le store partagé."""
    mods = {
        "generate_password": _load("h_genpwd", "functions/generate-password/handler.py"),
        "generate_2fa": _load("h_gen2fa", "functions/generate-2fa/handler.py"),
        "authenticate": _load("h_auth", "functions/authenticate/handler.py"),
    }
    for mod in mods.values():
        mod.db_connect = lambda s=store: FakeConn(s)
    return mods


def make_event(body):
    """Reproduit l'objet `event` du template python3-http (attribut .body)."""
    return types.SimpleNamespace(body=body)
