# tests/test_security.py
from tests.conftest import PASSWORD, csrf, login


def test_views_require_login(client):
    for path in ("/medico", "/medico/paciente/demo-001", "/paciente", "/paciente/demo-001"):
        resp = client.get(path)
        assert resp.status_code == 302 and "/login" in resp.headers["Location"], path


def test_api_requires_doctor(client, patient):
    assert client.get("/api/health").status_code == 200
    anon = client.application.test_client()
    assert anon.post("/api/compare-labs", json={}).status_code == 401
    assert patient.post("/api/compare-labs", json={}).status_code == 403


def test_patient_cannot_see_other_patient_or_doctor_views(patient):
    assert patient.get("/paciente/demo-002").status_code == 404
    assert patient.get("/medico").status_code == 403
    assert patient.get("/medico/paciente/demo-001").status_code == 403


def test_wrong_password_and_lockout(client):
    for _ in range(5):
        assert login(client, "medico.demo", "incorrecta").status_code == 401
    assert login(client, "medico.demo").status_code == 429   # bloqueado aunque la clave sea correcta


def test_post_without_csrf_rejected(doctor):
    resp = doctor.post("/medico/paciente/demo-002/recomendaciones", data={"text": "x"})
    assert resp.status_code == 400


def test_open_redirect_blocked(client):
    resp = client.post("/login", data={"username": "medico.demo", "password": PASSWORD,
                                       "next": "https://evil.example", "csrf_token": csrf(client)})
    assert resp.headers["Location"].endswith("/medico")


def test_login_redirects_back_to_next(client):
    resp = client.post("/login", data={"username": "medico.demo", "password": PASSWORD,
                                       "next": "/medico/paciente/demo-001", "csrf_token": csrf(client)})
    assert resp.headers["Location"].endswith("/medico/paciente/demo-001")


def test_security_headers_and_cookie(doctor):
    resp = doctor.get("/medico")
    assert "frame-ancestors 'none'" in resp.headers["Content-Security-Policy"]
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Cache-Control"] == "no-store"


def test_logout(doctor):
    doctor.post("/logout", data={"csrf_token": csrf(doctor)})
    assert doctor.get("/medico").status_code == 302


def test_production_requires_secret_key(monkeypatch):
    import pytest
    from flask import Flask
    from app.security import init_security
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        init_security(Flask("x"))
    monkeypatch.setenv("SECRET_KEY", "a" * 40)
    monkeypatch.setenv("DEMO_MODE", "1")
    monkeypatch.setenv("DEMO_PASSWORD", "x" * 5)  # demasiado corta
    with pytest.raises(RuntimeError):
        init_security(Flask("y"))
