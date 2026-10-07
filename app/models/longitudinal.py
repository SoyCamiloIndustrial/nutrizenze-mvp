# app/models/longitudinal.py
"""Comparación longitudinal de exámenes de laboratorio.

Genera alertas para revisión del profesional de salud (human-in-the-loop).
No diagnostica ni sugiere tratamiento: solo señala cambios entre dos tomas
que superan la variación esperada, o datos internamente inconsistentes, para
que el médico decida si repetir la prueba o investigar la causa.

Criterio principal: Valor de Cambio de Referencia (RCV),
    RCV% = 1.96 * sqrt(2) * sqrt(CVa^2 + CVi^2)
donde CVi es la variación biológica intraindividual y CVa la imprecisión
analítica. Un cambio menor al RCV puede explicarse por variación normal;
uno mayor sugiere un cambio real o un problema en alguna de las tomas.
"""
from datetime import date
from math import sqrt

Z_95 = 1.96

# CVi aproximados (base de datos de variación biológica EFLM / Ricos).
# CVa por defecto 3%; idealmente se reemplaza por el CVa declarado por cada laboratorio.
ANALYTES = {
    "glucose":           {"label": "Glucosa en ayunas", "cvi": 5.6,  "cva": 3.0},
    "total_cholesterol": {"label": "Colesterol total",  "cvi": 5.4,  "cva": 3.0},
    "hdl":               {"label": "Colesterol HDL",    "cvi": 7.1,  "cva": 3.0},
    "ldl":               {"label": "Colesterol LDL",    "cvi": 8.3,  "cva": 3.0},
    "triglycerides":     {"label": "Triglicéridos",     "cvi": 20.9, "cva": 3.0},
}

# Diferencia tolerada (mg/dL) entre el LDL reportado y el calculado por Friedewald.
FRIEDEWALD_TOLERANCE = 10.0


def rcv_percent(analyte):
    a = ANALYTES[analyte]
    return Z_95 * sqrt(2) * sqrt(a["cva"] ** 2 + a["cvi"] ** 2)


def friedewald_ldl(total_cholesterol, hdl, triglycerides):
    """LDL calculado (mg/dL). No es válido con triglicéridos >= 400."""
    if triglycerides >= 400:
        return None
    return total_cholesterol - hdl - triglycerides / 5.0


def _parse_date(value):
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _alert(code, severity, analyte, message, **detail):
    return {
        "code": code,
        "severity": severity,
        "analyte": analyte,
        "message": message,
        "detail": detail,
        "audience": "profesional",
        "requires_review": True,
    }


def check_internal_consistency(report):
    """Revisa un solo reporte: LDL reportado vs. calculado por Friedewald."""
    v = report.get("values", {})
    alerts = []
    needed = ("total_cholesterol", "hdl", "triglycerides")
    if not all(k in v for k in needed):
        return alerts
    calc = friedewald_ldl(v["total_cholesterol"], v["hdl"], v["triglycerides"])
    if calc is None:
        return alerts
    if "ldl" in v:
        diff = v["ldl"] - calc
        if abs(diff) > FRIEDEWALD_TOLERANCE:
            alerts.append(_alert(
                "LDL_INCONSISTENTE", "media", "ldl",
                f"El LDL reportado ({v['ldl']:g}) difiere {diff:+.1f} mg/dL del calculado "
                f"con Friedewald ({calc:.1f}). Puede ser LDL directo o un error de transcripción.",
                date=str(report.get("date")), lab=report.get("lab"),
                reported=v["ldl"], calculated=round(calc, 1),
            ))
    else:
        alerts.append(_alert(
            "LDL_NO_REPORTADO", "info", "ldl",
            f"El reporte no incluye LDL; el estimado por Friedewald es {calc:.1f} mg/dL"
            + (" (menos preciso con triglicéridos > 200)." if v["triglycerides"] > 200 else "."),
            date=str(report.get("date")), lab=report.get("lab"), calculated=round(calc, 1),
        ))
    return alerts


def compare_reports(previous, current):
    """Compara dos reportes y devuelve cambios por analito y alertas.

    Cada reporte: {"date": "YYYY-MM-DD", "lab": str, "fasting": bool|None,
                   "values": {analito: mg/dL}}
    """
    prev_date, curr_date = _parse_date(previous["date"]), _parse_date(current["date"])
    if curr_date < prev_date:
        previous, current = current, previous
        prev_date, curr_date = curr_date, prev_date

    pv, cv = previous.get("values", {}), current.get("values", {})
    changes, alerts = [], []

    for analyte in ANALYTES:
        if analyte not in pv or analyte not in cv or not pv[analyte]:
            continue
        before, after = pv[analyte], cv[analyte]
        pct = (after - before) / before * 100
        rcv = rcv_percent(analyte)
        significant = abs(pct) > rcv
        changes.append({
            "analyte": analyte,
            "label": ANALYTES[analyte]["label"],
            "before": before,
            "after": after,
            "change_abs": round(after - before, 1),
            "change_pct": round(pct, 1),
            "rcv_pct": round(rcv, 1),
            "exceeds_rcv": significant,
        })
        if significant:
            alerts.append(_alert(
                "CAMBIO_SIGNIFICATIVO", "alta" if abs(pct) > 2 * rcv else "media", analyte,
                f"{ANALYTES[analyte]['label']}: {before:g} → {after:g} mg/dL ({pct:+.1f}%) en "
                f"{(curr_date - prev_date).days} días; supera la variación esperada (±{rcv:.1f}%). "
                "Considerar repetir la prueba para descartar error preanalítico o analítico.",
                change_pct=round(pct, 1), rcv_pct=round(rcv, 1),
            ))

    for report in (previous, current):
        alerts.extend(check_internal_consistency(report))

    if previous.get("lab") and current.get("lab") and previous["lab"] != current["lab"]:
        alerts.append(_alert(
            "LABORATORIOS_DISTINTOS", "info", None,
            f"Las tomas provienen de laboratorios distintos ({previous['lab']} / {current['lab']}); "
            "diferencias de método y calibración pueden explicar parte del cambio.",
        ))

    fasting = (previous.get("fasting"), current.get("fasting"))
    if None in fasting or fasting[0] != fasting[1]:
        alerts.append(_alert(
            "AYUNO_NO_CONFIRMADO", "info", "triglycerides",
            "No se confirmó ayuno equivalente en ambas tomas; los triglicéridos son "
            "especialmente sensibles a esto.",
        ))

    return {
        "period_days": (curr_date - prev_date).days,
        "previous": {"date": str(prev_date), "lab": previous.get("lab")},
        "current": {"date": str(curr_date), "lab": current.get("lab")},
        "changes": changes,
        "alerts": alerts,
        "disclaimer": "Alertas para revisión del profesional de salud. "
                      "Vital Trace no emite diagnósticos ni indicaciones de tratamiento.",
    }
