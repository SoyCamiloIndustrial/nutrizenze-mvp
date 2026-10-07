# tests/test_views.py
from tests.conftest import csrf
from app.views import store


def test_portal_has_both_entries(client):
    html = client.get("/").get_data(as_text=True)
    assert "/medico" in html and "/paciente" in html


def test_doctor_sees_history_and_alerts(doctor):
    html = doctor.get("/medico/paciente/demo-001").get_data(as_text=True)
    assert "2026-03-12" in html and "2026-09-18" in html   # historial completo
    assert "Colesterol HDL" in html and "supera la variación esperada" in html
    assert "Sugerencia de Vital Trace" in html              # pendientes visibles al médico


def test_patient_sees_only_summary_and_approved(patient):
    html = patient.get("/paciente/demo-001").get_data(as_text=True)
    assert "2026-09-18" in html
    assert "2026-03-12" not in html                         # sin historial completo
    assert "variación esperada" not in html                 # sin alertas técnicas
    assert "Repetir perfil lipídico" not in html            # recomendación pendiente oculta
    assert "plan de alimentación" in html


def test_patient_home_redirects_to_own_summary(patient):
    resp = patient.get("/paciente")
    assert resp.headers["Location"].endswith("/paciente/demo-001")


def test_approval_publishes_to_patient(doctor):
    rec = store.add_recommendation("demo-002", "Caminar 30 minutos al día.", "Dra. Prueba")
    store.set_recommendation_status("demo-002", rec["id"], "pendiente")
    assert "Caminar 30 minutos" not in doctor.get("/paciente/demo-002").get_data(as_text=True)
    resp = doctor.post(f"/medico/paciente/demo-002/recomendaciones/{rec['id']}",
                       data={"action": "aprobar", "csrf_token": csrf(doctor)})
    assert resp.status_code == 302
    assert "Caminar 30 minutos" in doctor.get("/paciente/demo-002").get_data(as_text=True)


def test_doctor_adds_recommendation(doctor):
    doctor.post("/medico/paciente/demo-002/recomendaciones",
                data={"text": "Hidratación adecuada.", "author": "", "csrf_token": csrf(doctor)})
    assert "Hidratación adecuada." in doctor.get("/paciente/demo-002").get_data(as_text=True)


def test_unknown_patient_404(doctor):
    assert doctor.get("/paciente/no-existe").status_code == 404
    assert doctor.get("/medico/paciente/no-existe").status_code == 404


def test_api_info_moved(doctor):
    assert doctor.get("/api").get_json()["status"] == "online"
