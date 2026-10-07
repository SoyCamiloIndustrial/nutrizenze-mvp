# tests/test_longitudinal.py
# Datos sintéticos (no corresponden a ningún paciente real).
import pytest

from app.main import app
from app.models.longitudinal import compare_reports, friedewald_ldl, rcv_percent

PREVIOUS = {
    "date": "2026-01-10",
    "lab": "Laboratorio A",
    "fasting": True,
    "values": {"total_cholesterol": 180.0, "hdl": 30.0, "triglycerides": 360.0},
}
CURRENT = {
    "date": "2026-02-09",
    "lab": "Laboratorio B",
    "fasting": True,
    "values": {"total_cholesterol": 160.0, "hdl": 46.0, "ldl": 59.0,
               "triglycerides": 275.0, "glucose": 98.0},
}


def codes(result, analyte=None):
    return [a["code"] for a in result["alerts"] if analyte is None or a["analyte"] == analyte]


def test_rcv_triglycerides_is_wide():
    assert rcv_percent("triglycerides") == pytest.approx(58.5, abs=0.5)
    assert rcv_percent("hdl") == pytest.approx(21.4, abs=0.5)


def test_friedewald():
    assert friedewald_ldl(160, 46, 275) == pytest.approx(59.0)
    assert friedewald_ldl(200, 40, 450) is None


def test_hdl_jump_flagged_but_triglycerides_within_variation():
    result = compare_reports(PREVIOUS, CURRENT)
    by = {c["analyte"]: c for c in result["changes"]}
    assert by["triglycerides"]["change_pct"] == pytest.approx(-23.6, abs=0.1)
    assert not by["triglycerides"]["exceeds_rcv"]
    assert by["hdl"]["exceeds_rcv"]
    assert codes(result, "hdl") == ["CAMBIO_SIGNIFICATIVO"]
    assert "CAMBIO_SIGNIFICATIVO" not in codes(result, "triglycerides")
    assert result["period_days"] == 30


def test_context_alerts():
    result = compare_reports(PREVIOUS, CURRENT)
    assert "LDL_NO_REPORTADO" in codes(result, "ldl")      # reporte anterior sin LDL
    assert "LDL_INCONSISTENTE" not in codes(result)         # el actual cuadra con Friedewald
    assert "LABORATORIOS_DISTINTOS" in codes(result)
    assert "AYUNO_NO_CONFIRMADO" not in codes(result)
    assert all(a["audience"] == "profesional" and a["requires_review"] for a in result["alerts"])


def test_ldl_inconsistent_and_order_independent():
    bad = dict(CURRENT, values=dict(CURRENT["values"], ldl=95.0))
    result = compare_reports(bad, PREVIOUS)  # orden invertido
    assert result["previous"]["date"] == "2026-01-10"
    assert "LDL_INCONSISTENTE" in codes(result, "ldl")


def test_endpoint():
    client = app.test_client()
    resp = client.post("/api/compare-labs", json={"previous": PREVIOUS, "current": CURRENT})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "success"
    assert client.post("/api/compare-labs", json={}).status_code == 400
    bad = client.post("/api/compare-labs", json={"previous": {"date": "x"}, "current": CURRENT})
    assert bad.status_code == 400
