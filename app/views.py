# app/views.py
"""Vistas web: entrada para médicos y entrada para pacientes.

- Médico: historial completo de exámenes, comparaciones y alertas, y gestión
  de recomendaciones (solo las aprobadas llegan al paciente).
- Paciente: resumen del último examen y recomendaciones aprobadas.

Requiere sesión: el médico ve todos los pacientes; cada paciente solo el suyo.
"""
from flask import Blueprint, abort, g, redirect, render_template, request, url_for

try:
    from app.models.longitudinal import ANALYTES, compare_reports
    from app.models.patient_store import PatientStore
    from app.security import audit, role_required
except ImportError:  # ejecutado como `python app/main.py`
    from models.longitudinal import ANALYTES, compare_reports
    from models.patient_store import PatientStore
    from security import audit, role_required

views = Blueprint("views", __name__)
store = PatientStore()

# Rangos de referencia para el resumen del paciente (ATP III / ADA, mg/dL).
# (límite "en rango", límite "fuera de rango"); higher_is_better invierte el sentido.
PATIENT_RANGES = {
    "glucose":           {"limits": (100, 126)},
    "total_cholesterol": {"limits": (200, 240)},
    "ldl":               {"limits": (130, 160)},
    "triglycerides":     {"limits": (150, 200)},
    "hdl":               {"limits": (40, 40), "higher_is_better": True},
}
LEVEL_TEXT = {
    "ok": "En rango",
    "atencion": "Un poco fuera de rango",
    "alto": "Fuera de rango",
}


def classify(analyte, value):
    cfg = PATIENT_RANGES[analyte]
    low, high = cfg["limits"]
    if cfg.get("higher_is_better"):
        return "ok" if value >= low else "alto"
    if value < low:
        return "ok"
    return "atencion" if value < high else "alto"


def patient_comparisons(patient):
    """Compara cada toma con la anterior (más reciente primero)."""
    reports = patient["reports"]
    return [compare_reports(a, b) for a, b in zip(reports, reports[1:])][::-1]


def collect_alerts(comparisons):
    """Alertas de todas las comparaciones, sin repetir las de un mismo reporte."""
    seen, out = set(), []
    for c in comparisons:
        for a in c["alerts"]:
            if a["message"] in seen:
                continue
            seen.add(a["message"])
            out.append(dict(a, period=f'{c["previous"]["date"]} → {c["current"]["date"]}'))
    return out


def review_alerts(comparisons):
    return [a for a in collect_alerts(comparisons) if a["severity"] in ("media", "alta")]


def _patient_or_404(patient_id):
    patient = store.get(patient_id)
    if patient is None:
        abort(404)
    return patient


@views.route("/")
def portal():
    return render_template("portal.html")


# ===== MÉDICO =====
@views.route("/medico")
@role_required("medico")
def doctor_home():
    rows = []
    for p in store.all():
        comps = patient_comparisons(p)
        rows.append({
            "patient": p,
            "last_date": p["reports"][-1]["date"] if p["reports"] else None,
            "n_reports": len(p["reports"]),
            "n_alerts": len(review_alerts(comps)),
            "n_pending": sum(r["status"] == "pendiente" for r in p["recommendations"]),
        })
    return render_template("doctor_list.html", rows=rows)


@views.route("/medico/paciente/<patient_id>")
@role_required("medico")
def doctor_patient(patient_id):
    patient = _patient_or_404(patient_id)
    audit("ver_historial", paciente=patient_id)
    analytes = [a for a in ANALYTES if any(a in r["values"] for r in patient["reports"])]
    comparisons = patient_comparisons(patient)
    return render_template(
        "doctor_patient.html",
        patient=patient,
        analytes=analytes,
        labels={k: v["label"] for k, v in ANALYTES.items()},
        comparisons=comparisons,
        alerts=collect_alerts(comparisons),
    )


@views.route("/medico/paciente/<patient_id>/recomendaciones", methods=["POST"])
@role_required("medico")
def doctor_add_recommendation(patient_id):
    _patient_or_404(patient_id)
    text = request.form.get("text", "").strip()
    if text:
        author = request.form.get("author", "").strip() or g.user["name"]
        store.add_recommendation(patient_id, text[:1000], author[:120])
        audit("agregar_recomendacion", paciente=patient_id)
    return redirect(url_for("views.doctor_patient", patient_id=patient_id) + "#recomendaciones")


@views.route("/medico/paciente/<patient_id>/recomendaciones/<rec_id>", methods=["POST"])
@role_required("medico")
def doctor_review_recommendation(patient_id, rec_id):
    _patient_or_404(patient_id)
    status = {"aprobar": "aprobada", "descartar": "descartada"}.get(request.form.get("action"))
    if status is None or store.set_recommendation_status(patient_id, rec_id, status) is None:
        abort(400)
    audit("revisar_recomendacion", paciente=patient_id, recomendacion=rec_id, estado=status)
    return redirect(url_for("views.doctor_patient", patient_id=patient_id) + "#recomendaciones")


# ===== PACIENTE =====
@views.route("/paciente")
@role_required("paciente", "medico")
def patient_home():
    if g.user["role"] == "paciente":
        return redirect(url_for("views.patient_summary", patient_id=g.user["patient_id"]))
    return render_template("patient_select.html", patients=store.all())


@views.route("/paciente/<patient_id>")
@role_required("paciente", "medico")
def patient_summary(patient_id):
    # El paciente solo puede ver su propio resumen; el médico puede previsualizarlo.
    if g.user["role"] == "paciente" and g.user["patient_id"] != patient_id:
        abort(404)
    patient = _patient_or_404(patient_id)
    audit("ver_resumen", paciente=patient_id)
    reports = patient["reports"]
    latest = reports[-1] if reports else None
    items = []
    if latest:
        for analyte, value in latest["values"].items():
            if analyte not in PATIENT_RANGES:
                continue
            previous = next((r["values"][analyte] for r in reversed(reports[:-1]) if analyte in r["values"]), None)
            level = classify(analyte, value)
            items.append({
                "label": ANALYTES[analyte]["label"],
                "value": value,
                "level": level,
                "level_text": LEVEL_TEXT[level],
                "trend": None if previous is None else ("sube" if value > previous else "baja" if value < previous else "igual"),
            })
    approved = [r for r in patient["recommendations"] if r["status"] == "aprobada"]
    return render_template("patient_summary.html", patient=patient, latest=latest,
                           items=items, recommendations=approved)
