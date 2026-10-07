# tests/test_views.py
import pytest

from app.main import app
from app.views import store


@pytest.fixture
def client():
    return app.test_client()


def test_portal_has_both_entries(client):
    html = client.get("/").get_data(as_text=True)
    assert "/medico" in html and "/paciente" in html


def test_doctor_sees_history_and_alerts(client):
    html = client.get("/medico/paciente/demo-001").get_data(as_text=True)
    assert "2026-03-12" in html and "2026-09-18" in html   # historial completo
    assert "Colesterol HDL" in html and "supera la variación esperada" in html
    assert "Sugerencia de Vital Trace" in html              # pendientes visibles al médico


def test_patient_sees_only_summary_and_approved(client):
    html = client.get("/paciente/demo-001").get_data(as_text=True)
    assert "2026-09-18" in html
    assert "2026-03-12" not in html                         # sin historial completo
    assert "variación esperada" not in html                 # sin alertas técnicas
    assert "Repetir perfil lipídico" not in html            # recomendación pendiente oculta
    assert "plan de alimentación" in html


def test_approval_publishes_to_patient(client):
    rec = store.add_recommendation("demo-002", "Caminar 30 minutos al día.", "Dra. Prueba")
    store.set_recommendation_status("demo-002", rec["id"], "pendiente")
    assert "Caminar 30 minutos" not in client.get("/paciente/demo-002").get_data(as_text=True)
    resp = client.post(f"/medico/paciente/demo-002/recomendaciones/{rec['id']}", data={"action": "aprobar"})
    assert resp.status_code == 302
    assert "Caminar 30 minutos" in client.get("/paciente/demo-002").get_data(as_text=True)


def test_doctor_adds_recommendation(client):
    client.post("/medico/paciente/demo-002/recomendaciones", data={"text": "Hidratación adecuada.", "author": ""})
    assert "Hidratación adecuada." in client.get("/paciente/demo-002").get_data(as_text=True)


def test_unknown_patient_404(client):
    assert client.get("/paciente/no-existe").status_code == 404
    assert client.get("/medico/paciente/no-existe").status_code == 404


def test_api_info_moved(client):
    assert client.get("/api").get_json()["status"] == "online"
