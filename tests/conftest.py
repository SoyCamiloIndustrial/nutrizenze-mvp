# tests/conftest.py
import os
import secrets

os.environ.setdefault("DEMO_MODE", "1")
# Contraseña aleatoria por ejecución: no hay credenciales fijas en el repo.
os.environ.setdefault("DEMO_PASSWORD", secrets.token_urlsafe(16))
PASSWORD = os.environ["DEMO_PASSWORD"]

import pytest  # noqa: E402

from app.main import app  # noqa: E402
from app.security import _failed_logins  # noqa: E402


def csrf(client):
    client.get("/login")
    with client.session_transaction() as s:
        return s["csrf"]


def login(client, username, password=PASSWORD):
    return client.post("/login", data={"username": username, "password": password, "csrf_token": csrf(client)})


@pytest.fixture
def client():
    _failed_logins.clear()
    return app.test_client()


@pytest.fixture
def doctor(client):
    login(client, "medico.demo")
    return client


@pytest.fixture
def patient(client):
    login(client, "paciente.uno")
    return client
